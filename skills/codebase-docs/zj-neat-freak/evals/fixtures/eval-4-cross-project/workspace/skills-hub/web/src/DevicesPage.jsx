import { useEffect, useState } from 'react';

// “我的设备”——列出用户通过 Device Flow 授权过的设备
export function DevicesPage() {
  const [devices, setDevices] = useState([]);
  useEffect(() => {
    fetch('/api/auth/device/sessions').then(r => r.json()).then(setDevices);
  }, []);
  return (
    <ul>{devices.map(d => <li key={d.client_id}>{d.client_id} · {d.approved_at}</li>)}</ul>
  );
}
