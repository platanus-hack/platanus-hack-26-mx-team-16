export interface JwtSession {
  accessToken: string;
  refreshToken: string;
  expiresIn?: number | null;
  tokenType?: string | null;
}

export const emptyJwtSession: JwtSession = {
  accessToken: "",
  refreshToken: "",
  expiresIn: null,
  tokenType: null,
};
