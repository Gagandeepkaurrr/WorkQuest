import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api-client'
import type { Event } from '../../lib/types'
import { label } from '../../lib/types'
import { ErrorState,Loading } from '../../components/feedback/states'
export function TimelinePanel({branchId}:{branchId:string}){const events=useQuery({queryKey:['events',branchId],queryFn:()=>api<{items:Event[];inherited_prefix:Event[]}>(`/branches/${branchId}/events`)})
if(events.isPending)return <Loading/>;if(events.error)return <ErrorState error={events.error}/>
return <div className="stack"><div className="panel-heading"><h2>How you got here.</h2><p>A recorded history of your investigation. Reviewing it never re-runs an action.</p></div><ol className="timeline">{[...(events.data?.inherited_prefix??[]),...(events.data?.items??[])].map(e=><li className="glass" key={e.id}><span className="timeline-dot"/><div><span className="eyebrow">MINUTE {e.logical_tick}</span><h3>{label(e.type)}</h3><p>{typeof e.payload?.reply_text==='string'?e.payload.reply_text:typeof e.payload?.text==='string'?e.payload.text:JSON.stringify(e.payload?.result??e.payload?.payload??{})}</p></div><small>#{e.seq}</small></li>)}</ol></div>}
