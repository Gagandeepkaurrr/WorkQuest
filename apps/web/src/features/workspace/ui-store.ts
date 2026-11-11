import { create } from 'zustand'
import { persist } from 'zustand/middleware'
export const panels=['Team','Evidence','Tasks','Service','Actions','Notes','Timeline'] as const
export type Panel=typeof panels[number]
export const useWorkspaceUI=create<{panel:Panel;setPanel:(panel:Panel)=>void}>()(persist(set=>({panel:'Team',setPanel:panel=>set({panel})}),{name:'wq:workspace-ui'}))
