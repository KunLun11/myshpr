import { ApiError } from "@/lib/api";

/** Backend `code` values mapped to friendly Russian messages. */
const CODE_MESSAGES: Record<string, string> = {
  INVALID_CREDENTIALS: "Неверный email или пароль.",
  ACCOUNT_DISABLED: "Аккаунт отключён. Обратитесь к администратору школы.",
  ACCOUNT_DELETED: "Аккаунт больше недоступен.",
  ACCOUNT_LOCKED: "Слишком много неудачных попыток входа. Попробуйте через 15 минут.",
  RATE_LIMITED: "Слишком много попыток. Попробуйте через минуту.",
  EMAIL_TAKEN: "Этот email уже зарегистрирован. Попробуйте войти.",
  INVITE_NOT_FOUND: "Код приглашения не найден. Проверьте его у учителя.",
  INVITE_EXPIRED: "Срок действия кода истёк. Попросите у учителя новый код.",
  INVITE_REVOKED: "Код отозван. Попросите у учителя новый код.",
  INVITE_EXHAUSTED: "Код уже использован максимальное число раз.",
  SCHOOL_INACTIVE: "Школа недоступна для регистрации. Обратитесь к администратору.",
  INVALID_CURRENT_PASSWORD: "Текущий пароль указан неверно.",
  PASSWORD_UNCHANGED: "Новый пароль совпадает с текущим.",
  NO_REFRESH_TOKEN: "Сессия не найдена, войдите заново.",
  REFRESH_TOKEN_REUSED: "Сессия недействительна, войдите заново.",
  REFRESH_TOKEN_EXPIRED: "Сессия истекла, войдите заново.",
  NOT_AUTHENTICATED: "Требуется вход.",
  FORBIDDEN: "Недостаточно прав для этого действия.",
  ROLE_FORBIDDEN: "Недостаточно прав для этого действия.",
  SCHOOL_ACCESS_DENIED: "Нет доступа к этой школе.",
  CLASS_ACCESS_DENIED: "Нет доступа к этому классу.",
  VALIDATION_ERROR: "Проверьте заполненные поля.",
};

export function authErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "VALIDATION_ERROR" && error.errors.length > 0) {
      return error.errors.map((item) => item.message).join(" · ");
    }
    return CODE_MESSAGES[error.code] ?? error.message ?? "Не удалось выполнить действие.";
  }
  return "Сервис недоступен. Проверьте подключение и попробуйте снова.";
}
