import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthGuard } from '../components/guards/AuthGuard';
import { RoleGuard } from '../components/guards/RoleGuard';
import { AppLayout } from '../components/layout/AppLayout';
import { AccessDeniedPage } from '../pages/AccessDeniedPage';
import { ClientsPage } from '../pages/ClientsPage';
import { LoginPage } from '../pages/LoginPage';
import { OnboardingPage } from '../pages/OnboardingPage';
import { ProfilePage } from '../pages/ProfilePage';
import { ProjectsPage } from '../pages/ProjectsPage';
import { SitesPage } from '../pages/SitesPage';
import { AttendancePage } from '../pages/AttendancePage';
import { SupervisorAttendancePage } from '../pages/SupervisorAttendancePage';
import { DailyWorkEntryPage } from '../pages/DailyWorkEntryPage';
import { WorkOrdersPage } from '../pages/WorkOrdersPage';
import { ActivitiesPage } from '../pages/ActivitiesPage';
import { MaterialsPage } from '../pages/MaterialsPage';
import { SupervisorVerificationQueuePage } from '../pages/SupervisorVerificationQueuePage';
import { EmployeeDayVerificationPage } from '../pages/EmployeeDayVerificationPage';

export const AppRoutes: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Route */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/403" element={<AccessDeniedPage />} />

        {/* Authenticated Routes wrapped in AppLayout */}
        <Route element={<AuthGuard />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/profile" replace />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/attendance" element={<AttendancePage />} />

            {/* Employee Daily Work Route */}
            <Route element={<RoleGuard allowedRoles={['employee']} />}>
              <Route path="/daily-work" element={<DailyWorkEntryPage />} />
            </Route>

            {/* Supervisor & Admin Routes */}
            <Route element={<RoleGuard allowedRoles={['supervisor', 'administrator', 'director']} />}>
              <Route path="/supervisor/attendance" element={<SupervisorAttendancePage />} />
              <Route path="/verification" element={<SupervisorVerificationQueuePage />} />
              <Route path="/verification/:employeeId" element={<EmployeeDayVerificationPage />} />
            </Route>

            {/* Admin Only Routes */}
            <Route element={<RoleGuard allowedRoles={['administrator']} />}>
              <Route path="/onboarding" element={<OnboardingPage />} />
              <Route path="/admin/clients" element={<ClientsPage />} />
              <Route path="/admin/projects" element={<ProjectsPage />} />
              <Route path="/admin/sites" element={<SitesPage />} />
            </Route>

            {/* Admin & Director Master Data Routes */}
            <Route element={<RoleGuard allowedRoles={['administrator', 'director']} />}>
              <Route path="/admin/work-orders" element={<WorkOrdersPage />} />
              <Route path="/admin/activities" element={<ActivitiesPage />} />
              <Route path="/admin/materials" element={<MaterialsPage />} />
            </Route>
          </Route>
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/profile" replace />} />
      </Routes>
    </BrowserRouter>
  );
};
