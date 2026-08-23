import { registerPlugin } from '@capacitor/core'

/**
 * Native location-permission helpers used by the weather widget.
 * See LocationPermissionPlugin.java.
 */
export interface LocationPermissionPlugin {
  /** Open this app's system settings page so the user can change the permission. */
  openAppDetails(): Promise<void>
}

export const LocationPermission = registerPlugin<LocationPermissionPlugin>('LocationPermission')
