import { useCallback, useEffect, useState } from "react";
import {
  deletePlanItem,
  generatePlan as apiGeneratePlan,
  getCalendarRange,
  getPlan,
  logFeedback,
  updatePlanItem,
} from "../api";

export function usePlanning({ user, showToast, refreshTasks }) {
  const [planDate, setPlanDate] = useState(() => new Date().toISOString().substring(0, 10));
  const [schedule, setSchedule] = useState([]);
  const [unscheduled, setUnscheduled] = useState([]);
  const [calendarDays, setCalendarDays] = useState([]);
  const [modelVersion, setModelVersion] = useState("");
  const [modelConfidence, setModelConfidence] = useState(null);
  const [planning, setPlanning] = useState(false);

  const resetPlanning = useCallback(() => {
    setSchedule([]);
    setUnscheduled([]);
    setCalendarDays([]);
    setModelVersion("");
    setModelConfidence(null);
  }, []);

  const refreshPlan = useCallback(async () => {
    if (!user) {
      resetPlanning();
      return;
    }
    try {
      const data = await getPlan(planDate);
      setModelVersion(data.model_version || "");
      setModelConfidence(data.model_confidence ?? null);
      setSchedule(data.scheduled || []);
      setUnscheduled(data.unscheduled || []);
    } catch (err) {
      if (err?.response?.status === 404) {
        setSchedule([]);
        setUnscheduled([]);
        setModelVersion("");
        setModelConfidence(null);
      }
    }
  }, [planDate, resetPlanning, user]);

  const refreshCalendar = useCallback(async () => {
    if (!user) {
      setCalendarDays([]);
      return;
    }
    const d = new Date(planDate);
    const start = new Date(d.getFullYear(), d.getMonth(), 1).toISOString().substring(0, 10);
    const end = new Date(d.getFullYear(), d.getMonth() + 1, 0).toISOString().substring(0, 10);
    try {
      const res = await getCalendarRange(start, end);
      setCalendarDays(res.days || []);
    } catch (err) {
      console.error("Failed to load calendar", err);
      setCalendarDays([]);
    }
  }, [planDate, user]);

  const refreshPlanAndCalendar = useCallback(async () => {
    await refreshPlan();
    await refreshCalendar();
  }, [refreshPlan, refreshCalendar]);

  useEffect(() => {
    if (!user) {
      resetPlanning();
      return;
    }
    refreshPlanAndCalendar();
  }, [user, planDate, refreshPlanAndCalendar, resetPlanning]);

  const generatePlan = useCallback(async () => {
    if (!user) return;
    setPlanning(true);
    try {
      const data = await apiGeneratePlan(planDate);
      setModelVersion(data.model_version || "");
      setModelConfidence(data.model_confidence ?? null);
      setSchedule(data.scheduled || []);
      setUnscheduled(data.unscheduled || []);
      await refreshTasks?.();
      await refreshCalendar();
      showToast?.("AI planner generated your day.", "success");
    } catch (err) {
      console.error("Plan failed", err);
      showToast?.(err?.response?.data?.detail || "Unable to generate plan.", "error");
    } finally {
      setPlanning(false);
    }
  }, [planDate, refreshCalendar, refreshTasks, showToast, user]);

  const rescheduleItem = useCallback(
    async (planItemId, start, end) => {
      if (!planItemId) return;
      try {
        await updatePlanItem(planItemId, start, end);
        await refreshPlanAndCalendar();
        showToast?.("Updated schedule.", "success");
      } catch (err) {
        console.error("Reschedule failed", err);
        showToast?.("Could not update this item.", "error");
      }
    },
    [refreshPlanAndCalendar, showToast]
  );

  const deletePlanEntry = useCallback(
    async (planItemId) => {
      if (!planItemId) return;
      try {
        await deletePlanItem(planItemId);
        await refreshPlanAndCalendar();
        showToast?.("Removed from calendar.", "success");
      } catch (err) {
        console.error("Delete plan item failed", err);
        showToast?.("Could not remove this item.", "error");
      }
    },
    [refreshPlanAndCalendar, showToast]
  );

  const sendFeedback = useCallback(
    async ({ taskId, outcome }) => {
      if (!user) return;
      try {
        await logFeedback({ taskId, outcome });
        showToast?.("Feedback captured - the planner will adapt.", "success");
      } catch (err) {
        console.error("Feedback failed", err);
        showToast?.("Could not send feedback. Is the backend reachable?", "error");
      }
    },
    [showToast, user]
  );

  return {
    planDate,
    setPlanDate,
    schedule,
    unscheduled,
    calendarDays,
    modelVersion,
    modelConfidence,
    planning,
    generatePlan,
    refreshPlanAndCalendar,
    rescheduleItem,
    deletePlanEntry,
    sendFeedback,
  };
}
