export interface RequestContext {
  tenant?: string;
  accessToken?: string;
}

export const emptyRequestContext: RequestContext = {
  tenant: "",
  accessToken: "",
};
