export const emptyErrorFeedback = {
  errors: [],
  validation: null,
};

export const genericServerError = {
  errors: [
    {
      code: "client.ServerError",
      message: "Something went wrong.",
    },
  ],
  validation: null,
};

export const invalidCredentials = {
  errors: [
    {
      code: "auth.InvalidCredentials",
      message: "Invalid Credentials!",
    },
  ],
  validation: null,
};

export const invalidRefreshToken = {
  errors: [
    {
      code: "client.InvalidRefreshToken",
      message: "Invalid Refresh Token!",
    },
  ],
  validation: null,
};

export const refreshCookieNotFound = {
  errors: [
    {
      code: "client.RefreshCookieNotFound",
      message: "Invalid Refresh Token Cookie!",
    },
  ],
  validation: null,
};
