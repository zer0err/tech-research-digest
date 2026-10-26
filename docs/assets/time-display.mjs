// Absolute instants are stored with offsets. Only presentation uses the visitor's browser time zone.
export const executionZone = 'Asia/Shanghai';
export function visitorZone() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
}
export function dateInZone(value, zone) {
  return new Intl.DateTimeFormat('sv-SE', {timeZone: zone}).format(new Date(value));
}
export function timeInZone(value, zone) {
  return new Intl.DateTimeFormat('en-GB', {
    timeZone: zone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
  }).format(new Date(value));
}
export function timestampInZone(value, zone) {
  return `${dateInZone(value, zone)} ${timeInZone(value, zone)} · ${zone}`;
}
export function plannedInstant(executionDate, executionTime) {
  return `${executionDate}T${executionTime}:00+08:00`;
}
export function localizedTitle(title, instant, zone) {
  // The original execution/edition date remains in the article URL and data attributes.
  return title.replace(/（\d{4}-\d{2}-\d{2}）$/, `（${dateInZone(instant, zone)}）`);
}
