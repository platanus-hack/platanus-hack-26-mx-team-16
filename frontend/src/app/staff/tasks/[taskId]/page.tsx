import { StaffTaskDetailView } from "@/src/presentation/staff/staff-task-detail-view";

export default async function StaffTaskPage({
  params,
}: {
  params: Promise<{ taskId: string }>;
}) {
  const { taskId } = await params;
  return <StaffTaskDetailView taskId={taskId} />;
}
