import { useState } from "react";
import type { AppRecord, AppType } from "../../lib/api-types";
import { Button } from "../ui/button";
import { Input, Select, Textarea } from "../ui/input";

interface CreateAppFormProps {
  onCreate: (app: AppRecord) => void;
}

export function CreateAppForm({ onCreate }: CreateAppFormProps) {
  const [appId, setAppId] = useState("new_target");
  const [name, setName] = useState("New Target");
  const [type, setType] = useState<AppType>("web");
  const [platform, setPlatform] = useState("browser");

  return (
    <form
      className="grid gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        onCreate({ app_id: appId, name, type, platform });
      }}
    >
      <Input value={appId} onChange={(event) => setAppId(event.target.value)} aria-label="app id" />
      <Input value={name} onChange={(event) => setName(event.target.value)} aria-label="app name" />
      <div className="grid gap-3 sm:grid-cols-2">
        <Select value={type} onChange={(event) => setType(event.target.value as AppType)} aria-label="app type">
          <option value="pc_game">pc_game</option>
          <option value="pc_app">pc_app</option>
          <option value="web">web</option>
          <option value="android_app">android_app</option>
          <option value="android_game">android_game</option>
          <option value="other">other</option>
        </Select>
        <Input value={platform} onChange={(event) => setPlatform(event.target.value)} aria-label="platform" />
      </div>
      <Textarea readOnly value={'{"target_min":1000,"target_max":5000}'} aria-label="config json" />
      <Button variant="primary" type="submit">
        Create App
      </Button>
    </form>
  );
}
