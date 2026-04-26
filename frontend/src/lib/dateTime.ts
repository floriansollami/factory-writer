const ADMIN_TIME_ZONE = "Europe/Brussels";
const TIME_ZONE_OFFSET_PATTERN = /(?:Z|[+-]\d{2}:\d{2})$/;

export function formatAdminDateTime(value: string | null | undefined) {
  if (!value) {
    return "Non disponible";
  }

  const normalizedValue = TIME_ZONE_OFFSET_PATTERN.test(value) ? value : `${value}Z`;
  const date = new Date(normalizedValue);
  if (Number.isNaN(date.getTime())) {
    return "Non disponible";
  }

  return new Intl.DateTimeFormat("fr-FR", {
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
    timeZone: ADMIN_TIME_ZONE,
    timeZoneName: "short",
    year: "numeric",
  }).format(date);
}
