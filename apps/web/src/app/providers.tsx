import { QueryClient,QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
export const queryClient=new QueryClient({defaultOptions:{queries:{retry:1,staleTime:10000},mutations:{retry:false}}})
export function Providers({children}:{children:ReactNode}){return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>}
