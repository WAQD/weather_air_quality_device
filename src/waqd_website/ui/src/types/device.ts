export interface Device {
  id: string
  name: string | null
  device_id: string
  location?: string | null
  status: string
  last_seen?: string | null
  weather?: any
}