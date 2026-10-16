import { ButtonItem, Field, PanelSection, PanelSectionRow, ToggleField } from "@decky/ui";
import { callable, definePlugin } from "@decky/api";
import { useCallback, useEffect, useState } from "react";
import { FaComments } from "react-icons/fa";
import qrcode from "qrcode-generator";

type Status = {
  installed: boolean;
  bridge_version: string;
  notice: string;
  running: boolean;
  starting: boolean;
  url: string;
  version: string;
  error: string;
};

const getStatus = callable<[], Status>("get_status");
const startBridge = callable<[], Status>("start_bridge");
const stopBridge = callable<[], Status>("stop_bridge");
const getAutostart = callable<[], boolean>("get_autostart");
const setAutostart = callable<[enabled: boolean], boolean>("set_autostart");

const EMPTY: Status = { installed: true, bridge_version: "", notice: "", running: false, starting: false, url: "", version: "", error: "" };

function qrSvg(url: string): string {
  const qr = qrcode(0, "M");
  qr.addData(url);
  qr.make();
  return qr.createSvgTag({ cellSize: 4, margin: 4, scalable: true });
}

function Content() {
  const [status, setStatus] = useState<Status>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [auto, setAuto] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const s = await getStatus();
      setStatus((prev) => ({ ...s, error: prev.error && !s.running ? prev.error : "" }));
    } catch (e) {
      setStatus((prev) => ({ ...prev, error: "Could not reach the plugin backend." }));
    }
  }, []);

  useEffect(() => {
    refresh();
    getAutostart().then(setAuto).catch(() => {});
    const t = setInterval(refresh, 2000);
    return () => clearInterval(t);
  }, [refresh]);

  const toggle = async (on: boolean) => {
    setBusy(true);
    try {
      setStatus(on ? await startBridge() : await stopBridge());
    } catch (e) {
      setStatus((prev) => ({ ...prev, error: "Action failed." }));
    }
    setBusy(false);
  };

  const label = status.running ? "ON" : status.starting ? "Starting..." : "OFF";

  return (
    <PanelSection title="Phone chat bridge">
      {!status.installed && (
        <PanelSectionRow>
          <Field label="Bridge not installed" description="Reinstall the phonechatXI plugin zip; it carries the bridge." />
        </PanelSectionRow>
      )}
      <PanelSectionRow>
        <ToggleField
          label={"Bridge: " + label}
          checked={status.running || status.starting}
          disabled={busy || !status.installed}
          onChange={toggle}
        />
      </PanelSectionRow>
      {status.error && (
        <PanelSectionRow>
          <Field label="Problem" description={status.error} />
        </PanelSectionRow>
      )}
      {status.notice && (
        <PanelSectionRow>
          <Field label={status.notice} />
        </PanelSectionRow>
      )}
      {status.running && status.url && (
        <>
          <PanelSectionRow>
            <Field label="Phone address" description={status.url} />
          </PanelSectionRow>
          <PanelSectionRow>
            <div
              style={{ background: "#fff", borderRadius: 8, padding: 4, width: 200, margin: "0 auto" }}
              dangerouslySetInnerHTML={{ __html: qrSvg(status.url) }}
            />
          </PanelSectionRow>
        </>
      )}
      <PanelSectionRow>
        <ToggleField
          label="Start automatically"
          description="Start the bridge whenever Game Mode loads"
          checked={auto}
          onChange={async (v: boolean) => setAuto(await setAutostart(v))}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <Field label="Bridge version" description={status.bridge_version || "not installed"} />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={refresh}>
          Refresh
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}

export default definePlugin(() => ({
  name: "phonechatXI",
  titleView: <div>phonechatXI</div>,
  content: <Content />,
  icon: <FaComments />,
  onDismount() {},
}));
