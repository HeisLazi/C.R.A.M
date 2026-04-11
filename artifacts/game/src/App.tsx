import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import { useState, useEffect } from "react";

const queryClient = new QueryClient();

type NodeData = {
  id: string;
  type: string;
  subtype: string;
  biome: string;
  depth: number;
  difficulty: number;
  modifiers: string[];
  connections: string[];
  state: string;
  seed: number;
  god: string | null;
};

type Action = {
  id: string;
  label: string;
  type: string;
};

type GameState = {
  level: number;
  xp: number;
  hp: number;
  max_hp: number;
  modifiers: string[];
  insight: number;
};

const MODIFIER_DESCRIPTIONS: Record<string, string> = {
  glass_cannon: "Deal and take more damage",
  focused_mind: "Insight gains doubled",
  corrupted: "Enemies deal more damage",
  precision: "Streak bonuses increased",
};

function Overworld({
  sessionId,
  onEnterNode,
}: {
  sessionId: string;
  onEnterNode: () => void;
}) {
  const [world, setWorld] = useState<Record<string, NodeData>>({});
  const [currentNode, setCurrentNode] = useState<string>("");
  const [gameState, setGameState] = useState<GameState | null>(null);

  useEffect(() => {
    fetch(`/api/game/world/${sessionId}`)
      .then((res) => res.json())
      .then((data) => {
        setWorld(data.world);
        setCurrentNode(data.current_node);
        setGameState({
          level: data.level,
          xp: data.xp,
          hp: data.hp,
          max_hp: data.max_hp,
          modifiers: data.modifiers,
          insight: data.insight || 0,
        });
      });
  }, [sessionId]);

  if (!world || !currentNode || !gameState) {
    return <div className="p-8">Loading world...</div>;
  }

  const current = world[currentNode];
  const xpToNext = 50;
  const xpProgress = gameState.xp % xpToNext;
  const xpPercent = (xpProgress / xpToNext) * 100;

  const handleMove = (targetId: string) => {
    fetch("/api/game/move", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, target_node_id: targetId }),
    })
      .then((res) => res.json())
      .then((data) => {
        setCurrentNode(data.current_node);
      });
  };

  return (
    <div className="p-4">
      <div className="bg-gray-800 text-white p-3 rounded mb-4">
        <div className="flex justify-between items-center mb-2">
          <div>
            <span className="font-bold">Lv.{gameState.level}</span>
            <span className="ml-2 text-sm">XP: {gameState.xp}</span>
            <span className="ml-2 text-sm">
              HP: {gameState.hp}/{gameState.max_hp}
            </span>
            <span className="ml-2 text-sm text-cyan-400">
              Insight: {gameState.insight}/3
            </span>
          </div>
        </div>
        <div className="w-full bg-gray-700 rounded h-2">
          <div
            className="bg-yellow-500 h-2 rounded"
            style={{ width: `${xpPercent}%` }}
          />
        </div>
        <div className="mt-2 text-xs text-yellow-400">
          {gameState.modifiers
            .map((m) => MODIFIER_DESCRIPTIONS[m] || m)
            .join(" • ")}
        </div>
      </div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Overworld</h2>
        <button
          onClick={onEnterNode}
          className="px-4 py-2 bg-purple-600 text-white rounded"
        >
          Enter Node
        </button>
      </div>
      <div className="mb-2 text-sm">
        Current: <strong>{current.id}</strong> ({current.type} - {current.biome}
        )
      </div>
      <div className="grid grid-cols-4 gap-2">
        {Object.values(world).map((node) => (
          <button
            key={node.id}
            disabled={!current.connections.includes(node.id)}
            onClick={() => handleMove(node.id)}
            className={`p-2 border rounded text-xs ${
              node.id === currentNode
                ? "bg-green-500 text-white"
                : current.connections.includes(node.id)
                  ? "bg-white hover:bg-gray-100"
                  : "bg-gray-200 text-gray-500"
            }`}
          >
            {node.id}
            <br />
            <span className="text-[10px]">{node.type}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function NodeScreenWrapper({
  sessionId,
  onBack,
  onEnterAnomaly,
}: {
  sessionId: string;
  onBack: () => void;
  onEnterAnomaly: () => void;
}) {
  const [node, setNode] = useState<NodeData | null>(null);
  const [actions, setActions] = useState<Action[]>([]);

  useEffect(() => {
    fetch(`/api/game/node/${sessionId}`)
      .then((res) => res.json())
      .then((data) => {
        setNode(data.node);
        setActions(data.actions);
      });
  }, [sessionId]);

  if (!node) return <div className="p-8">Loading...</div>;

  const handleAction = (actionId: string) => {
    if (actionId === "leave") {
      onBack();
    } else if (actionId === "engage") {
      console.log("Combat action triggered");
    } else if (actionId === "investigate" || actionId === "stabilize") {
      onEnterAnomaly();
    } else {
      console.log("Action:", actionId);
    }
  };

  return (
    <div className="p-4">
      <button onClick={onBack} className="mb-4 text-sm underline">
        ← Back to Map
      </button>
      <div className="border p-4 rounded mb-4">
        <h3 className="text-lg font-bold">{node.type}</h3>
        <p className="text-sm">
          {node.subtype} • {node.biome} • Depth {node.depth} • Diff{" "}
          {node.difficulty}
        </p>
        {node.god && <p className="text-sm text-purple-600">God: {node.god}</p>}
      </div>
      <div className="space-y-2">
        {actions.map((action) => (
          <button
            key={action.id}
            onClick={() => handleAction(action.id)}
            className="w-full p-2 text-left border rounded hover:bg-gray-50"
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function AnomalyScreen({
  sessionId,
  onComplete,
}: {
  sessionId: string;
  onComplete: () => void;
}) {
  const [stepData, setStepData] = useState<any>(null);
  const [result, setResult] = useState<string>("");

  useEffect(() => {
    fetch(`/api/game/anomaly/${sessionId}`)
      .then((res) => res.json())
      .then((data) => setStepData(data.step_data));
  }, [sessionId]);

  const handleAnswer = (answer: string) => {
    fetch("/api/game/anomaly/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, answer }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.completed) {
          if (data.correct) {
            setResult(`Complete! +${data.reward?.xp || 10} XP`);
            setTimeout(onComplete, 1500);
          } else {
            setResult(`Failed. Correct: ${data.correct_answer}`);
            setTimeout(onComplete, 2000);
          }
        } else {
          setStepData(data.step_data);
        }
      });
  };

  if (!stepData) return <div className="p-8">Loading anomaly...</div>;

  if (result) {
    return <div className="p-8 text-center text-xl">{result}</div>;
  }

  return (
    <div className="p-4">
      <div className="mb-4 text-sm">
        Step {stepData.step + 1} of {stepData.total}
      </div>
      <div className="border p-4 rounded mb-4">
        <p className="text-lg mb-4">{stepData.question}</p>
        <div className="space-y-2">
          {stepData.options.map((opt: string) => (
            <button
              key={opt}
              onClick={() => handleAnswer(opt)}
              className="w-full p-2 border rounded hover:bg-blue-50"
            >
              {opt}
            </button>
          ))}
        </div>
      </div>
      <button onClick={onComplete} className="text-sm underline">
        Cancel
      </button>
    </div>
  );
}

function Game() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [screen, setScreen] = useState<
    "start" | "overworld" | "node" | "anomaly"
  >("start");

  const startGame = async () => {
    const res = await fetch("/api/game/start", { method: "POST" });
    const data = await res.json();
    setSessionId(data.session_id);
    setScreen("overworld");
  };

  if (screen === "anomaly" && sessionId) {
    return (
      <AnomalyScreen
        sessionId={sessionId}
        onComplete={() => setScreen("overworld")}
      />
    );
  }

  if (!sessionId || screen === "start") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <button
          onClick={startGame}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg text-lg"
        >
          Start New Game
        </button>
      </div>
    );
  }

  if (screen === "overworld") {
    return (
      <Overworld sessionId={sessionId} onEnterNode={() => setScreen("node")} />
    );
  }

  if (screen === "node" && sessionId) {
    return (
      <NodeScreenWrapper
        sessionId={sessionId}
        onBack={() => setScreen("overworld")}
        onEnterAnomaly={() => setScreen("anomaly")}
      />
    );
  }

  return <div>Loading...</div>;
}

function Router() {
  return (
    <Switch>
      <Route path="/" component={Game} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
