"use client";

import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import {
  type DocumentTypeField,
  FieldType,
} from "@/src/domain/entities/doctype";
import { FIELD_TYPE_META } from "@/src/presentation/components/field-type-meta";
import { Button } from "@/src/presentation/components/ui/button";
import { ExamplesEditor } from "@/src/presentation/components/ui/examples-editor";
import { Input } from "@/src/presentation/components/ui/input";
import { KeywordsInput } from "@/src/presentation/components/ui/keywords-input";
import { MarkdownRichEditor } from "@/src/presentation/components/ui/markdown-rich-editor";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/src/presentation/components/ui/select";

interface FieldDetailProps {
  field: DocumentTypeField;
  onBack: () => void;
  onUpdate?: (field: DocumentTypeField) => void;
  onSave?: () => void | Promise<void>;
  hideName?: boolean;
}

export function FieldDetail({
  field,
  onBack,
  onUpdate,
  onSave,
  hideName = false,
}: FieldDetailProps) {
  const t = useTranslations("FieldDetail");
  const [name, setName] = useState(field.name);
  const [description, setDescription] = useState(field.description || "");
  const [showDescription, setShowDescription] = useState(!!field.description);
  const [fieldType, setFieldType] = useState(field.type);
  const [keywords, setKeywords] = useState<string[]>(field.keywords ?? []);
  const [examples, setExamples] = useState<string[]>(field.examples ?? []);

  const handleNameChange = (value: string) => {
    setName(value);
    onUpdate?.({
      ...field,
      name: value,
    });
  };

  const handleDescriptionChange = (value: string) => {
    setDescription(value);
    onUpdate?.({
      ...field,
      description: value,
    });
  };

  const handleFieldTypeChange = (value: string | null) => {
    if (!value) return;
    setFieldType(value as FieldType);
    onUpdate?.({
      ...field,
      type: value as FieldType,
    });
  };

  const handleKeywordsChange = (next: string[]) => {
    setKeywords(next);
    onUpdate?.({ ...field, keywords: next });
  };

  const handleExamplesChange = (next: string[]) => {
    setExamples(next);
    onUpdate?.({ ...field, examples: next });
  };

  const handleSave = async () => {
    await onSave?.();
    onBack();
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {hideName ? (
          <div className="rounded-md border border-border/40 bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
            {t("arraySchemaHint")}
          </div>
        ) : (
          <div className="flex flex-col gap-2.5">
            <label className="text-sm font-medium">{t("fieldName")}</label>
            <Input
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder={t("fieldNamePlaceholder")}
            />
          </div>
        )}

        <div className="flex flex-col gap-2.5">
          <label className="text-sm font-medium">{t("dataType")}</label>
          <Select value={fieldType} onValueChange={handleFieldTypeChange}>
            <SelectTrigger className="w-full">
              {(() => {
                const meta = FIELD_TYPE_META[fieldType];
                if (!meta) return null;
                const Icon = meta.icon;
                return (
                  <span className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                    {meta.label}
                  </span>
                );
              })()}
            </SelectTrigger>
            <SelectContent>
              {Object.entries(FIELD_TYPE_META).map(([value, meta]) => {
                const Icon = meta.icon;
                return (
                  <SelectItem key={value} value={value}>
                    <Icon className="h-4 w-4 text-muted-foreground" />
                    {meta.label}
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-2.5">
          {showDescription ? (
            <>
              <label className="text-sm font-medium">{t("description")}</label>
              <MarkdownRichEditor
                value={description}
                onChange={handleDescriptionChange}
                placeholder={t("descriptionPlaceholder")}
                minHeight={200}
              />
            </>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              className="gap-2 p-0 h-auto text-sm text-primary hover:underline hover:bg-transparent"
              onClick={() => setShowDescription(true)}
            >
              <Plus className="h-4 w-4" />
              {t("addDescription")}
            </Button>
          )}
        </div>

        <div className="flex flex-col gap-2.5">
          <label className="text-sm font-medium">{t("keywords")}</label>
          <KeywordsInput
            value={keywords}
            onChange={handleKeywordsChange}
            placeholder={t("keywordsPlaceholder")}
          />
        </div>

        <div className="flex flex-col gap-2.5">
          <label className="text-sm font-medium">{t("examples")}</label>
          <ExamplesEditor value={examples} onChange={handleExamplesChange} />
        </div>
      </div>

      <div className="flex items-center justify-end gap-2 border-t border-border/50 px-4 py-3 bg-background">
        <Button variant="secondary" onClick={onBack}>
          {t("cancel")}
        </Button>
        <Button onClick={handleSave}>{t("save")}</Button>
      </div>
    </div>
  );
}
