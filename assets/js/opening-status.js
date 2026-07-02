(() => {
  const isEnglish = () => (document.documentElement.lang || "").toLowerCase().startsWith("en");
  const nowInJapan = () => {
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Tokyo", weekday: "short", hour: "2-digit", minute: "2-digit", hour12: false
    }).formatToParts(new Date()).reduce((acc, part) => { acc[part.type] = part.value; return acc; }, {});
    return { weekday: parts.weekday, hour: Number(parts.hour), minute: Number(parts.minute) };
  };
  const scheduleFor = (weekday) => {
    if (weekday === "Tue" || weekday === "Wed") return null;
    if (weekday === "Sat" || weekday === "Sun") return { open: 12, close: 19 };
    return { open: 13, close: 19 };
  };
  const buildMessage = () => {
    const now = nowInJapan();
    const schedule = scheduleFor(now.weekday);
    const en = isEnglish();
    if (!schedule) {
      return en
        ? { className: "closed", text: "Closed today. Regular holidays: Tuesdays and Wednesdays." }
        : { className: "closed", text: "本日は定休日です。定休日：火曜・水曜" };
    }
    const minutes = now.hour * 60 + now.minute;
    const openMin = schedule.open * 60;
    const closeMin = schedule.close * 60;
    if (minutes >= openMin && minutes < closeMin) {
      return en
        ? { className: "open", text: `Open now. Today's hours: ${schedule.open}:00–${schedule.close}:00.` }
        : { className: "open", text: `現在営業中です。本日の営業時間：${schedule.open}:00〜${schedule.close}:00` };
    }
    return en
      ? { className: "closed", text: `Closed now. Today's hours: ${schedule.open}:00–${schedule.close}:00.` }
      : { className: "closed", text: `現在営業時間外です。本日の営業時間：${schedule.open}:00〜${schedule.close}:00` };
  };
  const render = () => {
    const message = buildMessage();
    document.querySelectorAll("[data-opening-status]").forEach((el) => {
      el.classList.remove("open", "closed");
      el.classList.add(message.className);
      el.textContent = message.text;
    });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", render); else render();
})();
