export class ApiError extends Error {
  constructor(public code:string,message:string,public status:number,public requestId?:string){super(message)}
}
let csrfToken=''
export async function bootstrapCsrf():Promise<void>{
  const r=await fetch('/api/v1/auth/csrf',{credentials:'same-origin'})
  if(r.ok) csrfToken=(await r.json() as {csrf_token:string}).csrf_token
  else csrfToken=''
}
export async function api<T>(path:string,options:RequestInit={}):Promise<T>{
  const method=options.method??'GET'
  if(!['GET','HEAD'].includes(method)&&!csrfToken) await bootstrapCsrf()
  const response=await fetch(`/api/v1${path}`,{...options,credentials:'same-origin',headers:{'Content-Type':'application/json',...(csrfToken?{'X-CSRF-Token':csrfToken}:{}),...options.headers}})
  if(!response.ok){
    const b=await response.json().catch(()=>null) as {error?:{code:string;message:string};request_id?:string}|null
    throw new ApiError(b?.error?.code??'NETWORK_ERROR',b?.error?.message??'The service could not complete your request.',response.status,b?.request_id)
  }
  return response.json() as Promise<T>
}
export function write<T>(path:string,body:unknown={},method='POST',key?:string){
  return api<T>(path,{method,body:JSON.stringify(body),headers:key?{'Idempotency-Key':key}:{}})
}
export function errorMessage(error:unknown){return error instanceof Error?error.message:'Something went wrong. Please try again.'}
