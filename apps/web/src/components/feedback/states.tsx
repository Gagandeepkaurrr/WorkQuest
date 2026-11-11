import { LoaderCircle, TriangleAlert } from 'lucide-react'
import { errorMessage } from '../../lib/api-client'
export function Loading({label='Loading your workspace…'}:{label?:string}){return <div className="empty" role="status"><LoaderCircle className="spin"/><p>{label}</p></div>}
export function ErrorState({error,retry}:{error:unknown;retry?:()=>void}){return <div className="notice error" role="alert"><TriangleAlert size={20}/><div>{errorMessage(error)}{retry&&<button onClick={retry}>Try again</button>}</div></div>}
export function Empty({title,children}:{title:string;children?:React.ReactNode}){return <div className="empty"><h3>{title}</h3>{children}</div>}
