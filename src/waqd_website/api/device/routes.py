"""
Device Registration API endpoints for user-device pairing
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from waqd_website.auth.authentication import (
    user_exception_check,
)
from waqd_website.database.device_reg import (
    claim_session,
    confirm_registration,
    create_registration_session,
    expire_old_sessions,
    get_session_by_id,
)
from waqd_website.database.devices import delete_device as db_delete_device
from waqd_website.database.devices import (
    get_devices_for_user,
    update_device_status,
    update_device as db_update_device,
    add_device_owner,
)
from waqd_website.database import User
from waqd_website.database.user import get_user_by_id

rt = APIRouter()


# Request/Response models
class ClaimDeviceRequest(BaseModel):
    passphrase: str


class ClaimDeviceResponse(BaseModel):
    success: bool
    session_id: Optional[str] = None
    device_id: Optional[str] = None
    message: str


class DeviceResponse(BaseModel):
    id: int
    device_id: str
    name: Optional[str]
    location: Optional[str]
    status: str
    last_seen: Optional[datetime]


class DevicesListResponse(BaseModel):
    devices: List[DeviceResponse]
    total_count: int


class ConfirmRegistrationRequest(BaseModel):
    approved: bool


class InitiateRegistrationRequest(BaseModel):
    device_id: str
    location: str


class InitiateRegistrationResponse(BaseModel):
    success: bool
    session_id: str
    passphrase: str
    expires_at: str
    message: str


class PairingResponseRequest(BaseModel):
    session_id: str
    approved: bool


@rt.get("/devices", response_model=DevicesListResponse)
async def list_user_devices(current_user: User = user_exception_check):
    """
    Get all devices registered to the current user
    Returns real-time status from device_manager merged with DB data
    """
    from waqd_website.service.device_con import device_manager
    
    devices = get_devices_for_user(current_user.username)
    
    device_responses = []
    for device in devices:
        # Check if device is currently connected in device_manager
        is_connected = device.device_id in device_manager.connected_devices
        
        if is_connected:
            # Get real-time data from device_manager
            connected_device = device_manager.connected_devices[device.device_id]
            device_responses.append(
                DeviceResponse(
                    id=device.id or 0,
                    device_id=device.device_id,
                    name=device.name,
                    location=device.location,
                    status="online",  # Real-time status
                    last_seen=connected_device.last_seen_datetime,  # Real-time timestamp
                )
            )
        else:
            # Use DB data for offline devices
            device_responses.append(
                DeviceResponse(
                    id=device.id or 0,
                    device_id=device.device_id,
                    name=device.name,
                    location=device.location,
                    status=device.status,
                    last_seen=device.last_seen,
                )
            )
    
    return DevicesListResponse(
        devices=device_responses, 
        total_count=len(device_responses)
    )


@rt.delete("/devices/{device_id}")
async def delete_device(device_id: str, current_user: User = user_exception_check):
    """
    Delete/unlink a device from the current user
    """
    success = db_delete_device(device_id, current_user.username)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found or you don't have permission to delete it",
        )

    return {"success": True, "message": "Device deleted successfully"}


class UpdateDeviceRequest(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None


@rt.put("/devices/{device_id}")
async def update_device(
    device_id: str, 
    request: UpdateDeviceRequest,
    current_user: User = user_exception_check
):
    """
    Update device name and/or location
    """
    updated_device = db_update_device(
        device_id=device_id,
        username=current_user.username,
        name=request.name,
        location=request.location
    )

    if not updated_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found or you don't have permission to update it",
        )

    return {
        "success": True,
        "message": "Device updated successfully",
        "device": DeviceResponse(
            id=updated_device.id or 0,
            device_id=updated_device.device_id,
            name=updated_device.name,
            location=updated_device.location,
            status=updated_device.status,
            last_seen=updated_device.last_seen,
        )
    }


class AddDeviceOwnerRequest(BaseModel):
    username: str


@rt.post("/devices/{device_id}/share")
async def share_device(
    device_id: str,
    request: AddDeviceOwnerRequest,
    current_user: User = user_exception_check
):
    """
    Share a device with another user by adding them as an owner
    """
    success = add_device_owner(
        device_id=device_id,
        new_owner_username=request.username,
        current_owner_username=current_user.username
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to share device. User may not exist or device not found.",
        )

    return {
        "success": True,
        "message": f"Device successfully shared with {request.username}"
    }


# Pairing routines

@rt.post("/device/initiate-registration", response_model=InitiateRegistrationResponse)
async def initiate_device_registration(
    request: InitiateRegistrationRequest,
):
    if not request.device_id or len(request.device_id) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid device_id")

    # Create registration session
    session = create_registration_session(request.device_id, request.location)

    return InitiateRegistrationResponse(
        success=True,
        session_id=session.session_id,
        passphrase=session.passphrase,
        expires_at=session.expires_at.isoformat() + "Z",
        message="Registration session created. Display passphrase to user.",
    )


@rt.post("/devices/claim", response_model=ClaimDeviceResponse)
async def claim_device(request: ClaimDeviceRequest, current_user: User = user_exception_check):
    """
    User claims a device by entering the passphrase shown on device screen
    """
    from waqd_website.service.device_con import device_manager
    
    # Clean up expired sessions first
    expire_old_sessions()
    
    # Validate passphrase format
    passphrase = request.passphrase.strip().upper()
    if len(passphrase) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passphrase must be 6 characters"
        )
    
    # Attempt to claim the session
    if not current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not properly authenticated"
        )
    
    session_id = claim_session(passphrase, current_user.id)
    
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired passphrase"
        )
    
    # Get session details to return device_id
    session = get_session_by_id(session_id)
    
    if session:
        # Send pairing request to device via WebSocket
        await device_manager.send_pairing_request(
            session.device_id,
            current_user.username,
            session_id
        )
    
    return ClaimDeviceResponse(
        success=True,
        session_id=session_id,
        device_id=session.device_id if session else None,
        message="Device claimed. Waiting for device confirmation..."
    )


@rt.get("/devices/session/{session_id}/status")
async def get_session_status(session_id: str, current_user: User = user_exception_check):
    """
    Check the status of a registration session
    Used for polling while waiting for device confirmation
    """
    session = get_session_by_id(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Verify user owns this session
    if session.requesting_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )
    
    return {
        "session_id": session.session_id,
        "status": session.status,
        "device_id": session.device_id,
        "expires_at": session.expires_at.isoformat() + 'Z',
    }



@rt.post("/device/pairing-response")
async def device_pairing_response(
    request: PairingResponseRequest,
):
    """
    Device responds to a pairing request (user confirmation on device)
    This is called after the device shows a confirmation dialog to the user
    
    """
    import secrets
    from waqd_website.database.devices import update_device_api_key
    
    # TODO: Add proper device authentication
    
    if not request.session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id is required"
        )
    
    # Get session to find device_id
    session = get_session_by_id(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Confirm registration in database
    device = confirm_registration(request.session_id, request.approved)
    
    if device and request.approved:
        # Generate a long, secure API key (128 hex characters = 512 bits)
        api_key = secrets.token_hex(64)
        
        # Store API key in device record
        update_device_api_key(session.device_id, api_key)
        
        # Update device status to online
        update_device_status(session.device_id, "online")
        
        # Get user info for the response
        user = None
        if session.requesting_user_id:
            user = get_user_by_id(session.requesting_user_id)
        
        # Return API key in HTTP response so device can store it
        return {
            "success": True,
            "approved": True,
            "api_key": api_key,
            "user_info": {
                "username": user.username if user else None,
                "user_id": session.requesting_user_id
            },
            "message": "Device successfully paired"
        }
    else:
        return {
            "success": False,
            "approved": request.approved,
            "message": "Pairing rejected or failed"
        }


@rt.get("/device/session/{session_id}/check")
async def check_session_claimed(
    session_id: str,
):
    """
    Device polls this endpoint to check if user has claimed the session
    Returns whether session is claimed and by which user
        """
    session = get_session_by_id(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Get user info if session is claimed
    username = None
    if session.requesting_user_id:
        user = get_user_by_id(session.requesting_user_id)
        if user:
            username = user.username
    
    return {
        "session_id": session_id,
        "claimed": session.requesting_user_id is not None,
        "username": username,
        "status": session.status,
    }
