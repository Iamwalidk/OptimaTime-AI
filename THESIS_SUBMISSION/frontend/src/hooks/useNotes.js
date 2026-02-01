import { useCallback, useEffect, useState } from "react";
import { addNote, getNotes } from "../api";

export function useNotes({ user, showToast }) {
  const [notes, setNotes] = useState([]);
  const [noteDraft, setNoteDraft] = useState({ title: "", body: "" });

  const refreshNotes = useCallback(async () => {
    if (!user) {
      setNotes([]);
      return;
    }
    try {
      const data = await getNotes();
      setNotes(data);
    } catch (err) {
      console.error("Failed to load notes", err);
      showToast?.("Could not load notes.", "error");
    }
  }, [user, showToast]);

  const handleAddNote = useCallback(async () => {
    if (!noteDraft.title) return;
    try {
      await addNote(noteDraft);
      setNoteDraft({ title: "", body: "" });
      await refreshNotes();
    } catch (err) {
      console.error("Add note failed", err);
      showToast?.("Could not save note.", "error");
    }
  }, [noteDraft, refreshNotes, showToast]);

  useEffect(() => {
    if (!user) {
      setNotes([]);
      setNoteDraft({ title: "", body: "" });
    }
  }, [user]);

  return { notes, noteDraft, setNoteDraft, refreshNotes, handleAddNote };
}
