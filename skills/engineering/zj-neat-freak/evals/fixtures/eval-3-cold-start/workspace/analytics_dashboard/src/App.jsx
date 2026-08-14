import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';
import { supabase } from './lib/supabase';

export default function App() {
  const [events, setEvents] = useState([]);
  useEffect(() => {
    supabase.from('page_events').select('day, count').order('day').then(({ data }) => setEvents(data ?? []));
  }, []);
  return (
    <main>
      <h1>流量看板</h1>
      <LineChart width={720} height={320} data={events}>
        <XAxis dataKey="day" /><YAxis /><Tooltip />
        <Line type="monotone" dataKey="count" />
      </LineChart>
    </main>
  );
}
