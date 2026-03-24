/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class TimeTrackingDashboard extends Component {
    static template = "alpha_time_tracking.TimeTrackingDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            todayLabel: "",
            lines: [],
            dayId: false,
            activityDescription: "",
        });

        onWillStart(async () => {
            await this.loadTodayData();
        });
    }

    getTodayDateString() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, "0");
        const day = String(now.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    formatHeaderDate(dateStr) {
        const date = new Date(`${dateStr}T00:00:00`);
        return new Intl.DateTimeFormat("en-GB", {
            weekday: "long",
            day: "2-digit",
            month: "long",
            year: "numeric",
        }).format(date);
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

    async loadTodayData() {
        this.state.loading = true;

        const today = this.getTodayDateString();
        this.state.todayLabel = this.formatHeaderDate(today);

        const days = await this.orm.searchRead(
            "alpha.time.tracking.day",
            [["date", "=", today]],
            ["id", "activity_description", "line_ids"]
        );

        if (!days.length) {
            this.state.dayId = false;
            this.state.lines = [];
            this.state.activityDescription = "";
            this.state.loading = false;
            return;
        }

        const day = days[0];
        this.state.dayId = day.id;
        this.state.activityDescription = day.activity_description || "";

        const lines = await this.orm.searchRead(
            "alpha.time.tracking.line",
            [["day_id", "=", day.id]],
            ["id", "time_from", "time_to", "duration_minutes"]
        );

        this.state.lines = lines.map((line) => ({
            id: line.id,
            timeFrom: this.formatFloatTime(line.time_from),
            duration: this.formatDurationMinutes(line.duration_minutes || 0),
            timeTo: this.formatFloatTime(line.time_to),
        }));

        this.state.loading = false;
    }

    async onClickLogWorkingTime() {
        if (this.state.dayId) {
            await this.action.doAction({
                type: "ir.actions.act_window",
                name: "Edit Working Time",
                res_model: "alpha.time.tracking.day",
                res_id: this.state.dayId,
                views: [[false, "form"]],
                target: "new",
            });
        } else {
            await this.action.doAction({
                type: "ir.actions.act_window",
                name: "Log Working Time",
                res_model: "alpha.time.tracking.day",
                views: [[false, "form"]],
                target: "new",
                context: {
                    default_date: this.getTodayDateString(),
                },
            });
        }

        await this.loadTodayData();
    }
}

registry.category("actions").add("alpha_time_tracking.dashboard", TimeTrackingDashboard);