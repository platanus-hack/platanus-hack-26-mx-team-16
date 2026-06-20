import Ajv from "ajv";
import addFormats from "ajv-formats";
import type {
  JSONSchemaObject,
  ValidationError,
} from "@/src/domain/entities/json-schema";

const ajv = new Ajv({ allErrors: true, verbose: true });
addFormats(ajv);

export function validateSchema(schema: JSONSchemaObject): {
  isValid: boolean;
  errors: ValidationError[];
} {
  try {
    ajv.compile(schema);
    return { isValid: true, errors: [] };
  } catch (error: any) {
    return {
      isValid: false,
      errors: [
        {
          path: "",
          message: error.message || "Invalid schema",
          keyword: "schema",
          params: {},
        },
      ],
    };
  }
}

export function validateData(
  schema: JSONSchemaObject,
  data: any
): {
  isValid: boolean;
  errors: ValidationError[];
} {
  try {
    const validate = ajv.compile(schema);
    const isValid = validate(data);

    if (isValid) {
      return { isValid: true, errors: [] };
    }

    const errors: ValidationError[] = (validate.errors || []).map((err) => ({
      path: err.instancePath || err.schemaPath || "",
      message: err.message || "Validation error",
      keyword: err.keyword,
      params: err.params,
    }));

    return { isValid: false, errors };
  } catch (error: any) {
    return {
      isValid: false,
      errors: [
        {
          path: "",
          message: error.message || "Validation failed",
          keyword: "error",
          params: {},
        },
      ],
    };
  }
}
