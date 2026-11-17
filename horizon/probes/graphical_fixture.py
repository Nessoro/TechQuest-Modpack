"""Private X11 Horizon fixture shared by graphical gameplay probes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import tomllib
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from install_isolated_server import fresh_environment, verify


class GraphicalFixture:
    def __init__(self, server, work, version, world, player, module="prettypipes", frozen=False):
        self.server, self.work = server.resolve(), work.absolute()
        lock = verify(self.server)
        self.version = lock["modules"].get(module, {}).get("version")
        if self.version not in ((version,) if isinstance(version, str) else version):
            raise ValueError("unexpected content version")
        if (self.work.exists() or self.work.is_symlink()
                or any(p.is_symlink() for p in self.work.parents)
                or self.server in self.work.parents or self.work in self.server.parents):
            raise ValueError("work must be new and separate from the sealed installation")
        if not os.environ.get("DISPLAY") or len(player) > 16:
            raise ValueError("requires X11 display and a valid local fixture player name")
        self.config = tomllib.loads((self.server / "server.toml").read_text())
        self.engine = Path(self.config["engine"]["path"])
        self.ctl = self.engine.with_name("horizon-ctl")
        self.world, self.player = world, player
        self.frozen = frozen
        self.socket, self.rows = self.work / "control.sock", []
        self.game, self.log = None, None
        self.work.mkdir(mode=0o700, parents=True)
        shutil.copytree(self.server / "horizon-mods", self.work / "horizon-mods")
        shutil.copy2(self.server / "horizon-mods.txt", self.work / "horizon-mods.txt")
        (self.work / "eula.txt").write_text("eula=true\n")
        (self.work / "options.txt").write_text(
            "renderDistance:2\nsimulationDistance:2\nmaxFps:30\nguiScale:2\n"
            "pauseOnLostFocus:false\nfancyGraphics:false\n")

    def call(self, *words, timeout=60):
        result = subprocess.run([str(self.ctl), "--socket", str(self.socket), "--timeout", str(timeout),
                                 *map(str, words)], cwd=self.work, env=self.env,
                                capture_output=True, text=True, timeout=timeout + 5)
        reply = json.loads(result.stdout)
        self.rows.append({"phase": self.phase, "args": list(map(str, words)), "reply": reply})
        if result.returncode or "error" in reply:
            raise RuntimeError(f"control {words}: {reply}")
        return reply

    def settle(self):
        self.call("wait", 5)

    def command(self, line):
        reply = self.call("command", line)
        self.settle()
        return "\n".join(reply.get("chat", []))

    def start(self, phase):
        self.phase = phase
        self.env = fresh_environment(self.work / ("homes-" + phase))
        runtime = self.work / ("run-" + phase)
        runtime.mkdir(mode=0o700)
        self.env.update(HORIZON_PLAYER_NAME=self.player, XDG_RUNTIME_DIR=str(runtime),
                        XDG_CACHE_HOME=str(self.work / "cache"), LP_NUM_THREADS="2",
                        MESA_SHADER_CACHE_DIR=str(self.work / "cache/mesa"), WINIT_UNIX_BACKEND="x11")
        if self.frozen:
            self.env["HORIZON_STILL"] = "1"
        path = self.work / (phase + "-console.log")
        self.log = path.open("x"); path.chmod(0o600)
        self.game = subprocess.Popen([str(self.engine), "--resources", self.config["engine"]["resources"],
                                      "--game-dir", str(self.work), "--radius", "2",
                                      "--control-socket", str(self.socket)],
                                     cwd=self.work, env=self.env, stdout=self.log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 180
        while not self.socket.exists():
            if self.game.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError("graphical fixture did not start; inspect its private console log")
            time.sleep(.2)
        self.call("open", self.world, 263, "creative")
        self.call("wait-ready", timeout=180)
        self.call("resume")

    def stop(self):
        try:
            if self.game is not None and self.game.poll() is None:
                self.call("quit", timeout=30)
                self.game.wait(timeout=60)
            if self.game is not None and self.game.returncode != 0:
                raise RuntimeError(f"graphical engine exited {self.game.returncode}")
        finally:
            if self.game is not None and self.game.poll() is None:
                self.game.terminate(); self.game.wait(timeout=10)
            if self.log: self.log.close()
            self.game = None
            (self.work / "actions.json").write_text(json.dumps(self.rows, indent=2) + "\n")
