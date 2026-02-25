export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const profileId = localStorage.getItem('growora_profile_id')
  const lanToken = localStorage.getItem('growora_lan_token')
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (profileId) headers['X-Growora-Profile'] = profileId
  if (lanToken) headers['Authorization'] = `Bearer ${lanToken}`
  const res = await fetch(path, { headers, ...options })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
