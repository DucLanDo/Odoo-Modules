/** @odoo-module **/

import { Component, onWillStart, onMounted, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

class TimeTrackingDashboard extends Component {
    static template = "alpha_time_tracking.TimeTrackingDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dayStripWrapperRef = useRef("dayStripWrapper");

        const today = this.getTodayDateString();

        this.state = useState({
            loading: true,
            selectedDate: today,
            todayDate: today,
            selectedDateLabel: "",
            selectedMonthLabel: "",
            lines: [],
            dayId: false,
            dayStrip: [],
        });

        onWillStart(async () => {
            this.buildDayStrip();
            await this.loadSelectedDateData();
        });

        onMounted(() => {
            this.centerDayStripScroll();
            this.bindWheelScroll();
        });
    }

    getTodayDateString() {
        const now = new Date();
        return this.formatDateToYMD(now);
    }

    formatDateToYMD(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    parseYMDToDate(dateStr) {
        return new Date(`${dateStr}T00:00:00`);
    }

    formatHeaderDate(dateStr) {
        const date = this.parseYMDToDate(dateStr);
        return new Intl.DateTimeFormat("en-GB", {
            weekday: "long",
            day: "2-digit",
            month: "long",
            year: "numeric",
        }).format(date);
    }

    formatMonthLabel(dateStr) {
        const date = this.parseYMDToDate(dateStr);
        return new Intl.DateTimeFormat("en-GB", {
            month: "long",
            year: "numeric",
        }).format(date);
    }

    formatWeekdayShort(dateStr) {
        const date = this.parseYMDToDate(dateStr);
        return new Intl.DateTimeFormat("en-GB", {
            weekday: "short",
        }).format(date);
    }

    shiftSelectedDate(days) {
        const date = this.parseYMDToDate(this.state.selectedDate);
        date.setDate(date.getDate() + days);
        this.state.selectedDate = this.formatDateToYMD(date);
    }

    formatFloatTime(value) {
        if (value === false || value === null || value === undefined) {
            return "";
        }
        const hours = Math.floor(value);
        let minutes = Math.round((value - hours) * 60);

        let finalHours = hours;
        if (minutes === 60) {
            finalHours += 1;
            minutes = 0;
        }

        return `${finalHours}:${String(minutes).padStart(2, "0")}`;
    }

    formatDurationMinutes(totalMinutes) {
        const hours = Math.floor(totalMinutes / 60);
        const minutes = totalMinutes % 60;
        return `${hours}h ${minutes}m`;
    }

    formatDurationCompact(totalMinutes) {
        const hours = Math.floor(totalMinutes / 60);
        const minutes = totalMinutes % 60;
        return `${hours}:${String(minutes).padStart(2, "0")}`;
    }

    isEndOfWeek(dateStr) {
        const date = this.parseYMDToDate(dateStr);
        const day = date.getDay(); // 0 = Sunday
        return day === 0;
    }

    buildDayStrip() {
        const centerDate = this.parseYMDToDate(this.state.selectedDate);
        const days = [];

        for (let i = -30; i <= 30; i++) {
            const current = new Date(centerDate);
            current.setDate(centerDate.getDate() + i);

            const ymd = this.formatDateToYMD(current);
            days.push({
                date: ymd,
                dayNumber: current.getDate(),
                weekdayShort: this.formatWeekdayShort(ymd),
                totalMinutes: 0,
                totalDisplay: "",
                isSelected: ymd === this.state.selectedDate,
                isToday: ymd === this.state.todayDate,
                hasEntries: false,
                hasLeave: false,
                leaveType: "",
                leaveColor: "",
                leaveIconClass: "",
                isPublicHoliday: false,
                hoverLabel: "",
                isWeekSeparator: this.isEndOfWeek(ymd),
            });
        }

        this.state.dayStrip = days;
    }

    parseOdooUTCToLocalDate(datetimeStr, subtractOneSecond = false) {
        if (!datetimeStr) {
            return null;
        }

        const normalized = datetimeStr.replace("T", " ");
        const [datePart, timePart = "00:00:00"] = normalized.split(" ");
        const [year, month, day] = datePart.split("-").map(Number);
        const [hour, minute, second] = timePart.split(":").map(Number);

        let utcDate = new Date(Date.UTC(year, month - 1, day, hour, minute, second || 0));

        if (subtractOneSecond) {
            utcDate = new Date(utcDate.getTime() - 1000);
        }

        return this.formatDateToYMD(utcDate);
    }

    enumerateOdooDateRange(dateFromStr, dateToStr) {
        const startDateStr = this.parseOdooUTCToLocalDate(dateFromStr, false);
        const endDateStr = this.parseOdooUTCToLocalDate(dateToStr, true);

        if (!startDateStr || !endDateStr) {
            return [];
        }

        const start = this.parseYMDToDate(startDateStr);
        const end = this.parseYMDToDate(endDateStr);
        const result = [];

        const current = new Date(start);
        while (current <= end) {
            result.push(this.formatDateToYMD(current));
            current.setDate(current.getDate() + 1);
        }

        return result;
    }

    async loadDayStripTotals() {
        const dates = this.state.dayStrip.map((d) => d.date);
        if (!dates.length) {
            return;
        }

        const firstDate = dates[0];
        const lastDate = dates[dates.length - 1];

        const dayRecords = await this.orm.searchRead(
            "alpha.time.tracking.day",
            [["date", "in", dates]],
            ["id", "date", "total_minutes"]
        );

        const totalsByDate = {};
        for (const day of dayRecords) {
            totalsByDate[day.date] = day.total_minutes || 0;
        }

        // IMPORTANT:
        // We load all visible resource.calendar.leaves in the date range.
        // Access rights / record rules should already ensure the user only sees:
        // - own time offs
        // - public holidays
        const calendarLeaves = await this.orm.searchRead(
            "resource.calendar.leaves",
            [
                ["date_from", "<=", `${lastDate} 23:59:59`],
                ["date_to", ">=", `${firstDate} 00:00:00`],
            ],
            ["id", "name", "date_from", "date_to", "holiday_id", "time_off_type_display"]
        );

        const dateStateMap = {};

        for (const day of this.state.dayStrip) {
            const totalMinutes = totalsByDate[day.date] || 0;
            const hasEntries = totalMinutes > 0;

            dateStateMap[day.date] = {
                totalMinutes,
                totalDisplay: hasEntries ? this.formatDurationCompact(totalMinutes) : "",
                hasEntries,
                hasLeave: false,
                leaveType: "",
                leaveColor: "",
                leaveIconClass: "",
                isPublicHoliday: false,
                hoverLabel: "",
            };
        }

        const enumerateOdooDateRange = (dateFromStr, dateToStr) => {
            const startDateStr = this.parseOdooUTCToLocalDate(dateFromStr, false);
            const endDateStr = this.parseOdooUTCToLocalDate(dateToStr, true);

            if (!startDateStr || !endDateStr) {
                return [];
            }

            const start = this.parseYMDToDate(startDateStr);
            const end = this.parseYMDToDate(endDateStr);
            const result = [];

            const current = new Date(start);
            while (current <= end) {
                result.push(this.formatDateToYMD(current));
                current.setDate(current.getDate() + 1);
            }

            return result;
        };

        // First: public holidays (lower priority)
        for (const entry of calendarLeaves) {
            if (entry.holiday_id) {
                continue;
            }

            const coveredDates = enumerateOdooDateRange(entry.date_from, entry.date_to);
            for (const date of coveredDates) {
                if (!dateStateMap[date]) continue;

                dateStateMap[date].isPublicHoliday = true;
                dateStateMap[date].hoverLabel = entry.name || "Public Holiday";
                dateStateMap[date].leaveIconClass = "fa-calendar";
            }
        }

        // Second: own time offs (higher priority than public holiday)
        for (const entry of calendarLeaves) {
            if (!entry.holiday_id) {
                continue;
            }

            const coveredDates = enumerateOdooDateRange(entry.date_from, entry.date_to);
            const leaveTypeName = entry.time_off_type_display || "Time Off";

            for (const date of coveredDates) {
                if (!dateStateMap[date]) continue;

                dateStateMap[date].hasLeave = true;
                dateStateMap[date].leaveType = leaveTypeName;
                dateStateMap[date].leaveColor = "#6c757d";
                dateStateMap[date].leaveIconClass = "fa-user";
                dateStateMap[date].hoverLabel = leaveTypeName;
                dateStateMap[date].isPublicHoliday = false;
            }
        }

        this.state.dayStrip = this.state.dayStrip.map((day) => {
            const state = dateStateMap[day.date] || {};

            return {
                ...day,
                totalMinutes: state.totalMinutes || 0,
                totalDisplay: state.totalDisplay || "",
                hasEntries: !!state.hasEntries,
                hasLeave: !!state.hasLeave,
                leaveType: state.leaveType || "",
                leaveColor: state.leaveColor || "",
                leaveIconClass: state.leaveIconClass || "",
                isPublicHoliday: !!state.isPublicHoliday,
                hoverLabel: state.hoverLabel || "",
                isSelected: day.date === this.state.selectedDate,
                isToday: day.date === this.state.todayDate,
            };
        });
    }

    getDayBoxClass(day) {
        let classes = "o_alpha_tt_day_box";

        if (day.isSelected) {
            classes += " o_selected";
        } else if (day.hasLeave) {
            classes += " o_has_leave";
        } else if (day.isPublicHoliday) {
            classes += " o_public_holiday";
        } else if (day.hasEntries) {
            classes += " o_has_entries";
        } else if (day.isToday) {
            classes += " o_today";
        }

        if (day.isWeekSeparator) {
            classes += " o_week_separator";
        }

        return classes;
    }

    centerDayStripScroll() {
        const el = this.dayStripWrapperRef.el;
        if (!el) {
            return;
        }

        const centered = Math.max(0, (el.scrollWidth - el.clientWidth) / 2);
        el.scrollLeft = centered;
    }

    bindWheelScroll() {
        const el = this.dayStripWrapperRef.el;
        if (!el || el.__alphaWheelBound) {
            return;
        }

        el.addEventListener(
            "wheel",
            (ev) => {
                if (Math.abs(ev.deltaY) > Math.abs(ev.deltaX)) {
                    ev.preventDefault();
                    el.scrollLeft += ev.deltaY;
                }
            },
            { passive: false }
        );

        el.__alphaWheelBound = true;
    }

    async loadSelectedDateData() {
        this.state.loading = true;
        this.state.selectedDateLabel = this.formatHeaderDate(this.state.selectedDate);
        this.state.selectedMonthLabel = this.formatMonthLabel(this.state.selectedDate);

        this.buildDayStrip();
        await this.loadDayStripTotals();

        const days = await this.orm.searchRead(
            "alpha.time.tracking.day",
            [["date", "=", this.state.selectedDate]],
            ["id", "line_ids"]
        );

        if (!days.length) {
            this.state.dayId = false;
            this.state.lines = [];
            this.state.loading = false;
            this.centerDayStripScroll();
            return;
        }

        const day = days[0];
        this.state.dayId = day.id;

        const lines = await this.orm.searchRead(
            "alpha.time.tracking.line",
            [["day_id", "=", day.id]],
            ["id", "time_from", "time_to", "duration_minutes", "project_id", "activity_description"]
        );

        this.state.lines = lines.map((line) => ({
            id: line.id,
            timeFrom: this.formatFloatTime(line.time_from),
            duration: this.formatDurationMinutes(line.duration_minutes || 0),
            timeTo: this.formatFloatTime(line.time_to),
            projectName: line.project_id ? line.project_id[1] : "",
            activityDescription: line.activity_description || "",
        }));

        this.state.loading = false;
        this.centerDayStripScroll();
    }

    async onDateChange(ev) {
        this.state.selectedDate = ev.target.value;
        await this.loadSelectedDateData();
    }

    async onPreviousDay() {
        this.shiftSelectedDate(-1);
        await this.loadSelectedDateData();
    }

    async onNextDay() {
        this.shiftSelectedDate(1);
        await this.loadSelectedDateData();
    }

    async onToday() {
        this.state.selectedDate = this.state.todayDate;
        await this.loadSelectedDateData();
    }

    async onSelectDay(dayDate) {
        this.state.selectedDate = dayDate;
        await this.loadSelectedDateData();
    }

    async onClickEditWorkingTime() {
        const action = this.state.dayId
            ? {
                  type: "ir.actions.act_window",
                  name: "Edit Working Time",
                  res_model: "alpha.time.tracking.day",
                  res_id: this.state.dayId,
                  views: [[false, "form"]],
                  target: "new",
              }
            : {
                  type: "ir.actions.act_window",
                  name: "Edit Working Time",
                  res_model: "alpha.time.tracking.day",
                  views: [[false, "form"]],
                  target: "new",
                  context: {
                      default_date: this.state.selectedDate,
                  },
              };

        await this.action.doAction(action, {
            onClose: async () => {
                await this.loadSelectedDateData();
            },
        });
    }
}

registry.category("actions").add("alpha_time_tracking.dashboard", TimeTrackingDashboard);