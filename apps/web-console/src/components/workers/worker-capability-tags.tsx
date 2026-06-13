import { Badge } from "../ui/badge";

export function WorkerCapabilityTags({ capabilities }: { capabilities: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {capabilities.map((capability) => (
        <Badge key={capability} className="border-slate-700 bg-slate-950 text-slate-400">
          {capability}
        </Badge>
      ))}
    </div>
  );
}
