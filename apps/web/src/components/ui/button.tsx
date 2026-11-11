import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
export const cn=(...inputs:Parameters<typeof clsx>)=>twMerge(clsx(inputs))
const variants=cva('button',{variants:{variant:{primary:'button-primary',secondary:'button-secondary',ghost:'button-ghost',danger:'button-danger'},size:{default:'',small:'button-small'}},defaultVariants:{variant:'primary',size:'default'}})
export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>,VariantProps<typeof variants>{asChild?:boolean}
export const Button=forwardRef<HTMLButtonElement,ButtonProps>(({className,variant,size,asChild,...props},ref)=>{
 const Comp=asChild?Slot:'button';return <Comp className={cn(variants({variant,size}),className)} ref={ref} {...props}/>
})
Button.displayName='Button'
