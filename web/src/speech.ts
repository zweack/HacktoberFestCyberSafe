import { useEffect, useState } from "react";
import type { Language } from "./api/types";

export function useSpeech() {
  const [speaking, setSpeaking] = useState(false);
  const supported = typeof window !== "undefined" && "speechSynthesis" in window;
  useEffect(() => () => { if (supported) window.speechSynthesis.cancel(); }, [supported]);

  function speak(text: string, lang: Language) {
    if (!supported) return;
    const synth = window.speechSynthesis;
    synth.cancel();
    const u = new SpeechSynthesisUtterance(text);
    const tag = lang === "hi" ? "hi-IN" : "en-IN";
    u.lang = tag;
    u.rate = 0.9;
    const voices = synth.getVoices();
    u.voice = voices.find((v) => v.lang === tag) ?? voices.find((v) => v.lang.startsWith(lang)) ?? null;
    u.onend = u.onerror = () => setSpeaking(false);
    setSpeaking(true);
    synth.speak(u);
  }
  function stop() {
    if (supported) window.speechSynthesis.cancel();
    setSpeaking(false);
  }
  return { supported, speaking, speak, stop };
}
