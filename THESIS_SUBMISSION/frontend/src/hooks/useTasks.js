import { useCallback, useEffect, useState } from "react";
import { createTask, deleteTask, getTasks } from "../api";

export function useTasks({ user, showToast }) {
  const [tasks, setTasks] = useState([]);
  const [tasksLoading, setTasksLoading] = useState(false);

  const refreshTasks = useCallback(async () => {
    if (!user) {
      setTasks([]);
      return;
    }
    setTasksLoading(true);
    try {
      const data = await getTasks();
      setTasks(data);
    } catch (err) {
      console.error("Failed to load tasks", err);
      showToast?.("Cannot reach API. Is the backend running?", "error");
    } finally {
      setTasksLoading(false);
    }
  }, [user, showToast]);

  const handleTaskCreate = useCallback(
    async (task) => {
      if (!user) return;
      setTasksLoading(true);
      try {
        await createTask(task);
        await refreshTasks();
        showToast?.("Task added and ready for prioritization.", "success");
      } catch (err) {
        console.error("Task add failed", err);
        showToast?.("Could not add task. Please try again.", "error");
      } finally {
        setTasksLoading(false);
      }
    },
    [user, refreshTasks, showToast]
  );

  const handleTaskDelete = useCallback(
    async (taskId) => {
      if (!user) return;
      setTasksLoading(true);
      try {
        await deleteTask(taskId);
        await refreshTasks();
        showToast?.("Task removed from backlog.", "success");
      } catch (err) {
        console.error("Task delete failed", err);
        showToast?.("Could not remove task. Please try again.", "error");
      } finally {
        setTasksLoading(false);
      }
    },
    [user, refreshTasks, showToast]
  );

  useEffect(() => {
    refreshTasks();
  }, [refreshTasks]);

  return { tasks, tasksLoading, refreshTasks, handleTaskCreate, handleTaskDelete };
}
