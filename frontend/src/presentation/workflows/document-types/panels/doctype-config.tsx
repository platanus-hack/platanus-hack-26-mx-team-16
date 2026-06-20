"use client";

import { AlignLeft, CheckSquare, Code, Settings } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useDocumentTypeSchemaStore } from "src/application/stores/doctype-schema-store";
import type {
  DocumentType,
  DocumentTypeField,
  ValidationRule,
} from "src/domain/entities/doctype";
import { FieldType } from "src/domain/entities/doctype";
import { FieldDetail } from "src/presentation/components/field-detail";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "src/presentation/components/ui/tabs";
import { ValidationRuleDetail } from "src/presentation/components/validation-rule-detail";
import { DocumentTypeFieldsTab } from "../tabs/fields";
import { DocumentTypeSchemaTab } from "../tabs/schema";
import { DocumentTypeSettingsTab } from "../tabs/settings";
import { DocumentTypeValidationTab } from "../tabs/validation";

interface DocumentTypeMetadataPaneProps {
  doctype: DocumentType;
  onUpdate: () => void;
  onSave?: (
    payload: import("src/domain/repositories/doctype").UpdateDocumentTypePayload
  ) => Promise<void>;
  onImport?: (
    payload: import("src/domain/repositories/doctype").UpdateDocumentTypePayload
  ) => Promise<void>;
  onDelete?: () => Promise<void>;
  onPersistImport?: () => Promise<void>;
  onPersistValidationRules?: (
    rules: import("src/domain/repositories/doctype").ValidationRulePayload[]
  ) => Promise<void>;
  onSuggestFieldsStarted?: () => void;
}

const DOCTYPE_TABS = ["fields", "validation", "schema", "settings"] as const;
type DoctypeTab = (typeof DOCTYPE_TABS)[number];
const DEFAULT_DOCTYPE_TAB: DoctypeTab = "fields";

export function DocumentTypeConfigPanel({
  doctype,
  onUpdate,
  onSave,
  onImport,
  onDelete,
  onPersistImport,
  onPersistValidationRules,
  onSuggestFieldsStarted,
}: DocumentTypeMetadataPaneProps) {
  const t = useTranslations("DocumentTypes.tabs");
  const router = useRouter();
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const initialTab: DoctypeTab = (DOCTYPE_TABS as readonly string[]).includes(
    tabParam ?? ""
  )
    ? (tabParam as DoctypeTab)
    : DEFAULT_DOCTYPE_TAB;
  const [activeTab, setActiveTab] = useState<DoctypeTab>(initialTab);

  const handleTabChange = useCallback(
    (value: string) => {
      setActiveTab(value as DoctypeTab);
      const next = new URLSearchParams(searchParams.toString());
      next.set("tab", value);
      router.replace(`?${next.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );
  const [selectedValidationRule, setSelectedValidationRule] =
    useState<ValidationRule | null>(null);
  const [fieldsExpandedIds, setFieldsExpandedIds] = useState<Set<string>>(
    () => new Set()
  );

  const fields = useDocumentTypeSchemaStore((s) => s.fields);

  const fieldParam = searchParams.get("field");
  const { selectedField, selectedFieldIsArrayItem } = useMemo(() => {
    if (!fieldParam)
      return {
        selectedField: null as DocumentTypeField | null,
        selectedFieldIsArrayItem: false,
      };
    return findFieldByUuid(fields, fieldParam);
  }, [fields, fieldParam]);

  const selectField = useCallback(
    (field: DocumentTypeField) => {
      const next = new URLSearchParams(searchParams.toString());
      next.set("field", field.uuid);
      router.push(`?${next.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const closeFieldDetail = useCallback(() => {
    router.back();
  }, [router]);
  const initialize = useDocumentTypeSchemaStore((s) => s.initialize);
  const initializeFromSchema = useDocumentTypeSchemaStore(
    (s) => s.initializeFromSchema
  );
  const setFields = useDocumentTypeSchemaStore((s) => s.setFields);
  const updateField = useDocumentTypeSchemaStore((s) => s.updateField);

  const initializedUuidRef = useRef<string | null>(null);
  useEffect(() => {
    if (initializedUuidRef.current === doctype.uuid) return;
    initializedUuidRef.current = doctype.uuid;
    if (doctype.fields && Object.keys(doctype.fields).length > 0) {
      initializeFromSchema(
        doctype.uuid,
        doctype.fields as import("src/application/use-cases/json-schema/doctype-schema-converter").JsonSchemaNode
      );
    } else {
      initialize(doctype.uuid, []);
    }
  }, [doctype.uuid, doctype.fields, initialize, initializeFromSchema]);

  // ─── Field detail handlers ──────────────────────
  const handleFieldUpdate = (updatedField: DocumentTypeField) => {
    updateField(updatedField);
  };

  const handleFieldSave = useCallback(async () => {
    if (!onSave) return;
    const jsonSchema = useDocumentTypeSchemaStore.getState().jsonSchema;
    await onSave({ fields: jsonSchema as Record<string, unknown> });
  }, [onSave]);

  // If a validation rule is selected, show only the detail view
  if (selectedValidationRule) {
    return (
      <div className="bg-muted/50 w-full h-full">
        <ValidationRuleDetail
          rule={selectedValidationRule}
          onBack={() => setSelectedValidationRule(null)}
          onUpdate={(updatedRule) => {
            setSelectedValidationRule(updatedRule);
            onUpdate();
          }}
        />
      </div>
    );
  }

  // If a field is selected, show only the detail view
  if (selectedField) {
    return (
      <div className="bg-muted/50 w-full h-full">
        <FieldDetail
          field={selectedField}
          onBack={closeFieldDetail}
          onUpdate={handleFieldUpdate}
          onSave={handleFieldSave}
          hideName={selectedFieldIsArrayItem}
        />
      </div>
    );
  }

  return (
    <div className="bg-muted/50 grid grid-rows-[auto_1fr] w-full h-full">
      <Tabs
        value={activeTab}
        onValueChange={handleTabChange}
        className="w-full grid grid-rows-subgrid row-span-2"
      >
        {/* Header - Tabs */}
        <div className="border-b border-border/50 px-4 overflow-x-auto">
          <TabsList variant="line" className="h-12 w-full justify-between">
            <TabsTrigger
              variant="line"
              value="fields"
              className="gap-2 text-muted-foreground data-active:text-blue-500 hover:text-blue-400"
            >
              <AlignLeft className="h-4 w-4" />
              <span className="text-sm">{t("fields")}</span>
            </TabsTrigger>
            <TabsTrigger
              variant="line"
              value="validation"
              className="gap-2 text-muted-foreground data-active:text-blue-500 hover:text-blue-400"
            >
              <CheckSquare className="h-4 w-4" />
              <span className="text-sm">{t("validation")}</span>
            </TabsTrigger>
            <TabsTrigger
              variant="line"
              value="schema"
              className="gap-2 text-muted-foreground data-active:text-blue-500 hover:text-blue-400"
            >
              <Code className="h-4 w-4" />
              <span className="text-sm">{t("schema")}</span>
            </TabsTrigger>
            <TabsTrigger
              variant="line"
              value="settings"
              className="gap-2 text-muted-foreground data-active:text-blue-500 hover:text-blue-400"
            >
              <Settings className="h-4 w-4" />
              <span className="text-sm">{t("settings")}</span>
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Content */}
        <div className="flex-1 h-full overflow-hidden">
          <TabsContent value="fields" className="mt-0 h-full">
            <DocumentTypeFieldsTab
              doctype={doctype}
              fields={fields}
              onFieldsChange={setFields}
              onUpdate={onUpdate}
              onSelectField={selectField}
              onPersistImport={onPersistImport}
              onSuggestFieldsStarted={onSuggestFieldsStarted}
              expandedIds={fieldsExpandedIds}
              onExpandedIdsChange={setFieldsExpandedIds}
            />
          </TabsContent>

          <TabsContent value="validation" className="mt-0 h-full">
            <DocumentTypeValidationTab
              doctype={doctype}
              onUpdate={onUpdate}
              onPersistRules={onPersistValidationRules}
            />
          </TabsContent>

          <TabsContent value="schema" className="mt-0 h-full">
            <DocumentTypeSchemaTab doctype={doctype} />
          </TabsContent>

          <TabsContent value="settings" className="mt-0 h-full">
            <DocumentTypeSettingsTab
              doctype={doctype}
              onUpdate={onUpdate}
              onSave={onSave}
              onImport={onImport}
              onDelete={onDelete}
            />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}

function findFieldByUuid(
  fields: DocumentTypeField[],
  uuid: string,
  parentType?: FieldType
): {
  selectedField: DocumentTypeField | null;
  selectedFieldIsArrayItem: boolean;
} {
  for (const f of fields) {
    if (f.uuid === uuid) {
      return {
        selectedField: f,
        selectedFieldIsArrayItem: parentType === FieldType.ARRAY,
      };
    }
    if (f.children?.length) {
      const result = findFieldByUuid(f.children, uuid, f.type);
      if (result.selectedField) return result;
    }
  }
  return { selectedField: null, selectedFieldIsArrayItem: false };
}
