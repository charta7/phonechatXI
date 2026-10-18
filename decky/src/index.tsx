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
const newLink = callable<[], Status>("new_link");
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
  const [armed, setArmed] = useState(false);

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
        <ButtonItem
          layout="below"
          disabled={busy || !status.installed}
          description="Use this if someone else saw your link or QR. Your phone has to scan again."
          onClick={async () => {
            if (!armed) {
              setArmed(true);
              setTimeout(() => setArmed(false), 4000);
              return;
            }
            setArmed(false);
            setBusy(true);
            try {
              setStatus(await newLink());
            } catch (e) {
              setStatus((prev) => ({ ...prev, error: "Could not make a new link." }));
            }
            setBusy(false);
          }}
        >
          {armed ? "Tap again to replace the link" : "New phone link"}
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <Field label="Bridge version" description={status.bridge_version || "not installed"} />
      </PanelSectionRow>
      <PanelSectionRow>
        <Field label="This plugin is optional" description="The game can start the bridge too: /pchat config. Use one or the other." />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={refresh}>
          Refresh
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}

const PEARL = "data:image/png;base64,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";

export default definePlugin(() => ({
  name: "phonechatXI",
  titleView: <div style={{ display: "flex", alignItems: "center", gap: "8px" }}><img src={PEARL} width={22} height={22} alt="" />phonechatXI</div>,
  content: <Content />,
  icon: <FaComments />,
  onDismount() {},
}));
