import type { components } from '../generated/api-types'
export type Mission=components['schemas']['MissionView']
export type BranchState=components['schemas']['BranchState']
export type WorldState=components['schemas']['VisibleWorldState']
export type Action=components['schemas']['VisibleAction']
export type Artifact=components['schemas']['ArtifactMetadata']
export type CommandResponse=components['schemas']['CommandResponse']
export type RunSummary={id:string;active_branch_id:string;scenario_title:string;scenario_slug:string;scenario_version_id:string;is_demo:boolean;is_admin_preview:boolean;created_at:string;archived:boolean;status:string;simulation_time:number;practice_mode:boolean}
export type Event={id:string;seq:number;type:string;logical_tick:number;state_revision:number;payload:Record<string,unknown>;created_at:string}
export const label=(s:string)=>s.replaceAll('_',' ').replaceAll('.',' › ')
export const display=(v:unknown)=>typeof v==='boolean'?(v?'Enabled':'Disabled'):typeof v==='object'?JSON.stringify(v):String(v??'—')
