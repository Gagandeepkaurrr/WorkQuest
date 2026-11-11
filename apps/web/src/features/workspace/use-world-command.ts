import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ApiError,write } from '../../lib/api-client'
import type { BranchState,CommandResponse } from '../../lib/types'
type Pending={key:string;body:{type:string;payload:Record<string,unknown>;expected_state_revision:number}}
export function useWorldCommand(state:BranchState|undefined){const client=useQueryClient();const [busy,setBusy]=useState(false);const [error,setError]=useState<unknown>();const [uncertain,setUncertain]=useState(false)
 const storageKey=`wq:pending:${state?.branch_id}`
 const pending=state?sessionStorage.getItem(storageKey):null
 async function execute(type:string,payload:Record<string,unknown>={}){if(!state||busy)return;const old=sessionStorage.getItem(storageKey);const request:Pending=old?JSON.parse(old) as Pending:{key:crypto.randomUUID(),body:{type,payload,expected_state_revision:state.state_revision}};sessionStorage.setItem(storageKey,JSON.stringify(request));setBusy(true);setError(undefined)
 try{const response=await write<CommandResponse>(`/branches/${state.branch_id}/commands`,request.body,'POST',request.key);sessionStorage.removeItem(storageKey);setUncertain(false);client.setQueryData(['state',state.branch_id],response);await client.invalidateQueries({queryKey:['events',state.branch_id]});await client.invalidateQueries({queryKey:['checkpoints',state.branch_id]});return response}catch(e){setError(e);if(e instanceof ApiError&&e.status<500){sessionStorage.removeItem(storageKey);setUncertain(false);await client.invalidateQueries({queryKey:['state',state.branch_id]})}else{setUncertain(true)}}finally{setBusy(false)}}
 return {execute,busy,error,uncertain:uncertain||Boolean(pending),recover:()=>execute('')}
}
