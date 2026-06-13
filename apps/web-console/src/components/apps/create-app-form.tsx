import { useState } from "react";
import type { AppRecord, AppType } from "../../lib/api-types";
import { Button } from "../ui/button";
import { Input, Select, Textarea } from "../ui/input";

interface CreateAppFormProps {
  onCreate: (app: AppRecord) => void;
}

export function CreateAppForm({ onCreate }: CreateAppFormProps) {
  const [appId, setAppId] = useState("new_target");
  const [name, setName] = useState("新采集目标");
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
      <Input value={appId} onChange={(event) => setAppId(event.target.value)} aria-label="应用 ID" />
      <Input value={name} onChange={(event) => setName(event.target.value)} aria-label="应用名称" />
      <div className="grid gap-3 sm:grid-cols-2">
        <Select value={type} onChange={(event) => setType(event.target.value as AppType)} aria-label="应用类型">
          <option value="pc_game">PC 游戏</option>
          <option value="pc_app">PC 软件</option>
          <option value="web">Web 应用</option>
          <option value="android_app">Android 应用</option>
          <option value="android_game">Android 游戏</option>
          <option value="other">其他类型</option>
        </Select>
        <Input value={platform} onChange={(event) => setPlatform(event.target.value)} aria-label="平台" />
      </div>
      <Textarea readOnly value={'{"target_min":1000,"target_max":5000}'} aria-label="config_json" />
      <Button variant="primary" type="submit">
        新建应用
      </Button>
    </form>
  );
}
