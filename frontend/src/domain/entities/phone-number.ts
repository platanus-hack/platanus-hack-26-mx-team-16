export interface RawPhoneNumber {
  dialCode: number;
  phoneNumber: string;
  isoCode: string;
  prefix?: string | null;
}

export interface PhoneNumber extends RawPhoneNumber {
  uuid: string;
  isVerified: boolean;
}
