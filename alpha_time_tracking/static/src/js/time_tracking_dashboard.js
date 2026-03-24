/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class TimeTrackingDashboard extends Component {
    static template = "alpha_time_tracking.TimeTrackingDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        const today = this.getTodayDateString();

        this.state = useState({
            loading: true,
            selectedDate: today,
            selectedDateLabel: "",
            lines: [],
            dayId: false,
        });

        onWillStart(async () => {
            await this.loadSelectedDateData();
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

    async loadSelectedDateData() {
        this.state.loading = true;
        this.state.selectedDateLabel = this.formatHeaderDate(this.state.selectedDate);

        const days = await this.orm.searchRead(
            "alpha.time.tracking.day",
            [["date", "=", this.state.selectedDate]],
            ["id", "line_ids"]
        );

        if (!days.length) {
            this.state.dayId = false;
            this.state.lines = [];
            this.state.loading = false;
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