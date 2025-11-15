import React, {useEffect, useState} from 'react';

export default function PaperVisualizer(){
  const [papers, setPapers] = useState([]);

  useEffect(()=>{
    async function load(){
      const res = await fetch('/api/papers');
      const j = await res.json();
      setPapers(j.papers || []);
    }
    load();
  },[])

  return (
    <div>
      <h3>Papers</h3>
      <ul>
        {papers.map((p, i)=> (
          <li key={i}>{p.title} — <small>{p.url}</small></li>
        ))}
      </ul>
    </div>
  )
}
