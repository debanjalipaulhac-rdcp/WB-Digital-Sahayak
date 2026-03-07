"use client"
import { useRouter } from 'next/navigation'
import React from 'react'
import {
    Select,
    SelectContent,
    SelectGroup,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
const DEPARTMENTS = ['Higher Education', 'Women & Child Development Department', 'Backward Classes', 'Health & Family Welfare']
function DepartMent({ q, dept }: { q?: string, dept?: string }) {
    const router = useRouter()
    return (
        <Select onValueChange={(e) => router.push(`/search?${q ? `q=${encodeURIComponent(q)}&` : ''}dept=${encodeURIComponent(e==="all"?"":e)}`)}>
            <SelectTrigger className="w-full">
                <SelectValue placeholder="category" />
            </SelectTrigger>
            <SelectContent>
                <SelectGroup>
                    <SelectItem value="all">None</SelectItem>
                    {DEPARTMENTS.map(dept => (
                        <SelectItem value={dept} key={dept}>{dept}</SelectItem>
                    ))}
                </SelectGroup>
            </SelectContent>
        </Select>
    )
}

export default DepartMent