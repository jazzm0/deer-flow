import {useCallback, useMemo, useSyncExternalStore} from "react";

import {applyThreadOverrides, DEFAULT_LOCAL_SETTINGS, type LocalSettings,} from "./local";
import {
  getBaseSettingsSnapshot,
  getThreadModelSnapshot,
  getThreadModeSnapshot,
  type LocalSettingsSetter,
  subscribe,
  updateLocalSettings,
  updateThreadSettings,
} from "./store";

export function useLocalSettings(): [LocalSettings, LocalSettingsSetter] {
    const settings = useSyncExternalStore(
        subscribe,
        getBaseSettingsSnapshot,
        () => DEFAULT_LOCAL_SETTINGS,
    );

    const setSettings = useCallback<LocalSettingsSetter>((key, value) => {
        updateLocalSettings(key, value);
    }, []);

    return [settings, setSettings];
}

export function useThreadSettings(
    threadId: string,
): [LocalSettings, LocalSettingsSetter] {
    const baseSettings = useSyncExternalStore(
        subscribe,
        getBaseSettingsSnapshot,
        () => DEFAULT_LOCAL_SETTINGS,
    );

    const threadModelName = useSyncExternalStore(
        subscribe,
        () => getThreadModelSnapshot(threadId),
        () => undefined,
    );

    const threadMode = useSyncExternalStore(
        subscribe,
        () => getThreadModeSnapshot(threadId),
        () => undefined,
    );

    const settings = useMemo(
        () => applyThreadOverrides(baseSettings, threadModelName, threadMode),
        [baseSettings, threadModelName, threadMode],
    );

    const setSettings = useCallback<LocalSettingsSetter>(
        (key, value) => {
            updateThreadSettings(threadId, key, value);
        },
        [threadId],
    );

    return [settings, setSettings];
}
