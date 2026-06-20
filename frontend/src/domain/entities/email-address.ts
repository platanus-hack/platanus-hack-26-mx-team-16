export interface RawEmailAddress {
  email: string;
  isVerified: boolean;
}

export interface EmailAddress extends RawEmailAddress {
  uuid: string;
}
