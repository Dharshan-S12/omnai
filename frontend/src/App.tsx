import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ChatView from "./views/ChatView";
import UploadView from "./views/UploadView";
import TaskListView from "./views/TaskListView";
import TaskDetailView from "./views/TaskDetailView";
import MonitorView from "./views/MonitorView";
import { EquipmentGraphView } from "./views/EquipmentGraphView";
import { EquipmentDetailView } from "./views/EquipmentDetailView";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<ChatView />} />
          <Route path="chat" element={<ChatView />} />
          <Route path="tasks" element={<TaskListView />} />
          <Route path="upload" element={<UploadView />} />
          <Route path="task/:id" element={<TaskDetailView />} />
          <Route path="equipment" element={<EquipmentGraphView />} />
          <Route path="equipment/:equipment_id" element={<EquipmentDetailView />} />
          <Route path="monitor" element={<MonitorView />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
