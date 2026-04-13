import {
  DEFAULT_LOCAL_SETTINGS,
  getLocalSettings,
  getThreadMode,
  getThreadModelName,
  LOCAL_SETTINGS_KEY,
  type LocalSettings,
  saveLocalSettings,
  saveThreadMode,
  saveThreadModelName,
  THREAD_MODE_KEY_PREFIX,
  THREAD_MODEL_KEY_PREFIX,
} from "./local";

type Listener = () => void;

export type LocalSettingsSetter = <K extends keyof LocalSettings>(
    key: K,
    value: Partial<LocalSettings[K]>,
) => void;

const listeners = new Set<Listener>();
const threadModelNames = new Map<string, string | undefined>();
const threadModes = new Map<string, LocalSettings["context"]["mode"]>();

let baseSettings: LocalSettings = DEFAULT_LOCAL_SETTINGS;
let baseSettingsLoaded = false;
let storageListenerRegistered = false;

function emitChange() {
    for (const listener of listeners) {
        listener();
    }
}

function ensureBaseSettingsLoaded() {
    if (baseSettingsLoaded || typeof window === "undefined") {
        return;
    }

    baseSettings = getLocalSettings();
    baseSettingsLoaded = true;
}

function ensureStorageListenerRegistered() {
    if (storageListenerRegistered || typeof window === "undefined") {
        return;
    }

    window.addEventListener("storage", handleStorage);
    storageListenerRegistered = true;
}

function mergeSettingsSection<K extends keyof LocalSettings>(
    settings: LocalSettings,
    key: K,
    value: Partial<LocalSettings[K]>,
): LocalSettings {
    return {
        ...settings,
        [key]: {
            ...settings[key],
            ...value,
        },
    } as LocalSettings;
}

function handleStorage(event: StorageEvent) {
    if (event.storageArea && event.storageArea !== localStorage) {
        return;
    }

    ensureBaseSettingsLoaded();

    if (event.key === null) {
        baseSettings = getLocalSettings();
        threadModelNames.clear();
        threadModes.clear();
        emitChange();
        return;
    }

    if (event.key === LOCAL_SETTINGS_KEY) {
        baseSettings = getLocalSettings();
        emitChange();
        return;
    }

    if (event.key.startsWith(THREAD_MODEL_KEY_PREFIX)) {
        const threadId = event.key.slice(THREAD_MODEL_KEY_PREFIX.length);
        threadModelNames.set(threadId, getThreadModelName(threadId));
        emitChange();
        return;
    }

    if (event.key.startsWith(THREAD_MODE_KEY_PREFIX)) {
        const threadId = event.key.slice(THREAD_MODE_KEY_PREFIX.length);
        threadModes.set(threadId, getThreadMode(threadId));
        emitChange();
        return;
    }
}

export function subscribe(listener: Listener): () => void {
    ensureBaseSettingsLoaded();
    ensureStorageListenerRegistered();
    listeners.add(listener);

    return () => {
        listeners.delete(listener);
    };
}

export function getBaseSettingsSnapshot(): LocalSettings {
    ensureBaseSettingsLoaded();
    return baseSettings;
}

export function getThreadModelSnapshot(threadId: string): string | undefined {
    ensureBaseSettingsLoaded();

    if (!threadModelNames.has(threadId)) {
        threadModelNames.set(threadId, getThreadModelName(threadId));
    }

    return threadModelNames.get(threadId);
}

export function getThreadModeSnapshot(
    threadId: string,
): LocalSettings["context"]["mode"] {
    ensureBaseSettingsLoaded();

    if (!threadModes.has(threadId)) {
        threadModes.set(threadId, getThreadMode(threadId));
    }

    return threadModes.get(threadId);
}

export const updateLocalSettings: LocalSettingsSetter = (key, value) => {
    ensureBaseSettingsLoaded();
    ensureStorageListenerRegistered();

    baseSettings = mergeSettingsSection(baseSettings, key, value);
    saveLocalSettings(baseSettings);
    emitChange();
};

export function updateThreadSettings<K extends keyof LocalSettings>(
    threadId: string,
    key: K,
    value: Partial<LocalSettings[K]>,
) {
    ensureBaseSettingsLoaded();
    ensureStorageListenerRegistered();

    const nextBaseSettings = mergeSettingsSection(baseSettings, key, value);
    baseSettings = nextBaseSettings;
    saveLocalSettings(baseSettings);

    if (key === "context") {
        const contextValue = value as Partial<LocalSettings["context"]>;

        if (Object.prototype.hasOwnProperty.call(contextValue, "model_name")) {
            const threadModelName = contextValue.model_name;
            threadModelNames.set(threadId, threadModelName);
            saveThreadModelName(threadId, threadModelName);
        }

        if (Object.prototype.hasOwnProperty.call(contextValue, "mode")) {
            const mode = contextValue.mode;
            threadModes.set(threadId, mode);
            saveThreadMode(threadId, mode);
        }
    }

    emitChange();
}
