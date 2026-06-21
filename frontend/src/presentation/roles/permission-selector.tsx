"use client";

import { Search, X } from "lucide-react";
import { useDeferredValue, useMemo, useState } from "react";
import { PERMISSIONS_CATALOG } from "@/src/domain/constants/permissions-catalog";
import { Button } from "@/src/presentation/components/ui/button";
import { Checkbox } from "@/src/presentation/components/ui/checkbox";
import {
  Dialog,
  DialogBackdrop,
  DialogClose,
  DialogHeader,
  DialogPopup,
  DialogTitle,
} from "@/src/presentation/components/ui/dialog";
import { Input } from "@/src/presentation/components/ui/input";

interface PermissionSelectorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selected: string[];
  onConfirm: (permissions: string[]) => void;
}

export function PermissionSelector({
  open,
  onOpenChange,
  selected,
  onConfirm,
}: PermissionSelectorProps) {
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);
  const [localSelected, setLocalSelected] = useState<string[]>(selected);

  const filteredCatalog = useMemo(() => {
    if (!deferredSearch.trim()) return PERMISSIONS_CATALOG;
    const term = deferredSearch.toLowerCase();
    return PERMISSIONS_CATALOG.map((cat) => ({
      ...cat,
      permissions: cat.permissions.filter(
        (p) =>
          p.label.toLowerCase().includes(term) ||
          p.code.toLowerCase().includes(term)
      ),
    })).filter((cat) => cat.permissions.length > 0);
  }, [deferredSearch]);

  const handleTogglePermission = (code: string) => {
    setLocalSelected((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const handleToggleCategory = (categoryId: string) => {
    const category = PERMISSIONS_CATALOG.find((c) => c.id === categoryId);
    if (!category) return;
    const codes = category.permissions.map((p) => p.code);
    const allSelected = codes.every((c) => localSelected.includes(c));
    if (allSelected) {
      setLocalSelected((prev) => prev.filter((c) => !codes.includes(c)));
    } else {
      setLocalSelected((prev) => [...new Set([...prev, ...codes])]);
    }
  };

  const isCategoryChecked = (categoryId: string) => {
    const category = PERMISSIONS_CATALOG.find((c) => c.id === categoryId);
    if (!category) return false;
    return category.permissions.every((p) => localSelected.includes(p.code));
  };

  const isCategoryIndeterminate = (categoryId: string) => {
    const category = PERMISSIONS_CATALOG.find((c) => c.id === categoryId);
    if (!category) return false;
    const some = category.permissions.some((p) =>
      localSelected.includes(p.code)
    );
    const all = category.permissions.every((p) =>
      localSelected.includes(p.code)
    );
    return some && !all;
  };

  const handleOpenChange = (value: boolean) => {
    if (value) {
      setLocalSelected(selected);
      setSearch("");
    }
    onOpenChange(value);
  };

  const handleConfirm = () => {
    onConfirm(localSelected);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="max-w-lg p-6">
        <DialogHeader className="flex flex-row items-center justify-between">
          <DialogTitle>Seleccionar Permisos</DialogTitle>
          <DialogClose className="rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100">
            <X className="h-4 w-4" />
          </DialogClose>
        </DialogHeader>

        <div className="relative mt-4">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar permisos..."
            value={search}
            onValueChange={setSearch}
            className="pl-9"
          />
        </div>

        <div className="mt-4 max-h-80 overflow-y-auto space-y-3">
          {filteredCatalog.map((category) => (
            <div key={category.id}>
              <label className="flex items-center gap-2 cursor-pointer py-1">
                <Checkbox
                  checked={isCategoryChecked(category.id)}
                  indeterminate={isCategoryIndeterminate(category.id)}
                  onCheckedChange={() => handleToggleCategory(category.id)}
                />
                <span className="text-sm font-semibold text-foreground">
                  {category.label}{" "}
                  <span className="text-muted-foreground font-normal">
                    ({category.permissions.length})
                  </span>
                </span>
              </label>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 pl-6 mt-1">
                {category.permissions.map((perm) => (
                  <label
                    key={perm.code}
                    className="flex items-center gap-2 cursor-pointer py-0.5"
                  >
                    <Checkbox
                      checked={localSelected.includes(perm.code)}
                      onCheckedChange={() => handleTogglePermission(perm.code)}
                    />
                    <span className="text-sm text-foreground">
                      {perm.label}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between mt-6">
          <span className="text-sm text-muted-foreground">
            {localSelected.length} permisos seleccionados
          </span>
          <Button onClick={handleConfirm}>Listo</Button>
        </div>
      </DialogPopup>
    </Dialog>
  );
}
