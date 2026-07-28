import { useTranslation } from "react-i18next";
import { Upload, AlertCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { ActionConfigWrapper } from "./action-config-wrapper";
import type { DeployScriptActionProps } from "../../types";
import { BULK_ACTION_STYLES } from "../../types";

export function DeployScriptConfig({
  scriptName,
  onScriptNameChange,
  scriptCode,
  onScriptCodeChange,
  scriptEnable,
  onScriptEnableChange,
  scriptRun,
  onScriptRunChange,
  onExecute,
  onCancel,
}: DeployScriptActionProps) {
  const { t } = useTranslation();

  const handleFileSelect = (file: File | undefined) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      onScriptCodeChange(String(reader.result ?? ""));
      if (!scriptName.trim()) {
        onScriptNameChange(file.name.replace(/\.(js|mjs)$/i, ""));
      }
    };
    reader.readAsText(file);
  };

  const isExecuteDisabled = !scriptName.trim() || !scriptCode.trim();

  const uploadLinkClass = "text-sm text-primary cursor-pointer hover:underline";

  return (
    <ActionConfigWrapper
      title={t("bulkActions.deployScript")}
      icon={<Upload className="h-4 w-4" />}
      onExecute={onExecute}
      onCancel={onCancel}
      isExecuteDisabled={isExecuteDisabled}
    >
      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="script-name">{t("bulkActions.scriptName")}</Label>
          <Input
            id="script-name"
            value={scriptName}
            onChange={(e) => onScriptNameChange(e.target.value)}
            placeholder="my-script"
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="script-code">{t("bulkActions.scriptCode")}</Label>
            <label className={uploadLinkClass}>
              {t("bulkActions.uploadScriptFile")}
              <input
                type="file"
                accept=".js,.mjs,text/javascript"
                className="hidden"
                onChange={(e) => handleFileSelect(e.target.files?.[0])}
              />
            </label>
          </div>
          <Textarea
            id="script-code"
            value={scriptCode}
            onChange={(e) => onScriptCodeChange(e.target.value)}
            placeholder={"Shelly.addStatusHandler(function (status) {...})"}
            className="font-mono text-sm min-h-[220px]"
          />
        </div>

        <div className="flex items-center space-x-2">
          <Checkbox
            id="script-enable"
            checked={scriptEnable}
            onCheckedChange={(checked) =>
              onScriptEnableChange(checked === true)
            }
          />
          <Label htmlFor="script-enable" className="font-normal">
            {t("bulkActions.scriptEnable")}
          </Label>
        </div>

        <div className="flex items-center space-x-2">
          <Checkbox
            id="script-run"
            checked={scriptRun}
            onCheckedChange={(checked) => onScriptRunChange(checked === true)}
          />
          <Label htmlFor="script-run" className="font-normal">
            {t("bulkActions.scriptRun")}
          </Label>
        </div>

        <div className={BULK_ACTION_STYLES.infoBox}>
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-5 w-5 text-blue-600" />
            <span className="font-medium text-blue-800">
              {t("bulkActions.deployScriptNote")}
            </span>
          </div>
          <p className="text-sm text-blue-700 mt-2">
            {t("bulkActions.deployScriptDescription")}
          </p>
        </div>
      </div>
    </ActionConfigWrapper>
  );
}
