# Implementation Plan

> **Note:** The requirements.md document is currently empty. This task list is based on the design.md specifications. Requirements references below correspond to the design document sections.

## Phase 1: Foundation & Infrastructure

- [x] 1. Set up backend project structure with FastAPI and uv+ruff





  - [x] 1.1 Initialize Python project with uv, configure pyproject.toml with dependencies (FastAPI, SQLAlchemy, Pydantic, Redis, Celery, bcrypt, PyJWT, Hypothesis)


    - _Requirements: Design - Tech stack specification_

  - [x] 1.2 Configure ruff for linting and formatting

    - _Requirements: Design - Tech stack specification_
  - [x] 1.3 Create directory structure: app/models, app/schemas, app/api, app/services, app/repositories, app/middleware, app/tasks, app/utils


    - _Requirements: Design - Backend project structure_
  - [x] 1.4 Set up config.py with environment variable loading and settings management


    - _Requirements: Design - Configuration management_


- [x] 2. Set up database models and migrations








  - [x] 2.1 Create SQLAlchemy base model with tenant_id mixin and common fields (created_at, updated_at)


    - _Requirements: Design - Data Models, Property 1_

  - [x] 2.2 Implement Tenant model (id, name, slug, domain, subscription_plan, status, settings, timestamps)

    - _Requirements: Design - Data Models (TENANTS entity)_

  - [x] 2.3 Implement User model with role enum and password_hash

    - _Requirements: Design - Data Models (USERS entity)_

  - [x] 2.4 Implement Student model with all fields and relationships

    - _Requirements: Design - Data Models (STUDENTS entity)_

  - [x] 2.5 Implement Teacher model with subjects and classes_assigned arrays

    - _Requirements: Design - Data Models (TEACHERS entity)_
  - [x] 2.6 Implement Class, Section, Subject models with relationships


    - _Requirements: Design - Data Models (CLASSES, SECTIONS, SUBJECTS entities)_
  - [x] 2.7 Implement Attendance model with status enum


    - _Requirements: Design - Data Models (ATTENDANCE entity)_
  - [x] 2.8 Implement Exam and Grade models


    - _Requirements: Design - Data Models (EXAMS, GRADES entities)_
  - [x] 2.9 Implement Fee model with payment tracking


    - _Requirements: Design - Data Models (FEES entity)_
  - [x] 2.10 Implement Timetable model with day/period/time fields




    - _Requirements: Design - Data Models (TIMETABLE entity)_
  - [x] 2.11 Implement Announcement and LeaveRequest models


    - _Requirements: Design - Data Models (ANNOUNCEMENTS, LEAVE_REQUESTS entities)_
  - [x] 2.12 Create Alembic migration for all models


    - _Requirements: Design - Database schema_

- [x] 3. Implement multi-tenancy middleware and core services





  - [x] 3.1 Create TenantMiddleware to extract tenant from subdomain/header and inject into request state


    - _Requirements: Design - Components (TenantMiddleware)_
  - [x] 3.2 Write property test for tenant extraction






    - **Property 2: Tenant-Prefixed Cache Keys**
    - **Validates: Design - Property 2**
  - [x] 3.3 Implement TenantAwareRepository base class with automatic tenant_id filtering


    - _Requirements: Design - Components (Base Repository)_
  - [x] 3.4 Write property test for tenant data isolation






    - **Property 1: Tenant Data Isolation**
    - **Validates: Design - Property 1**
  - [x] 3.5 Implement CacheService with tenant-prefixed keys


    - _Requirements: Design - Components (Cache Service)_
  - [x] 3.6 Write property test for cache key format






    - **Property 2: Tenant-Prefixed Cache Keys**
    - **Validates: Design - Property 2**

- [x] 4. Checkpoint - Ensure all tests pass








  - Ensure all tests pass, ask the user if questions arise.

## Phase 2: Authentication & Authorization

- [x] 5. Implement authentication service





  - [x] 5.1 Create AuthService with password hashing (bcrypt) and verification


    - _Requirements: Design - Components (Authentication Service)_
  - [x] 5.2 Write property test for password hash round-trip











    - **Property 4: Password Hash Verification Round-Trip**
    - **Validates: Design - Property 4**
  - [x] 5.3 Implement JWT token creation with user_id, tenant_id, role claims


    - _Requirements: Design - Components (Authentication Service)_
  - [x] 5.4 Implement JWT token verification and decoding




    - _Requirements: Design - Components (Authentication Service)_
  - [x] 5.5 Write property test for JWT token round-trip













    - **Property 5: JWT Token Round-Trip**
    - **Validates: Design - Property 5**

  - [x] 5.6 Create auth dependency for FastAPI routes to extract current user

    - _Requirements: Design - Components (Authentication Service)_

- [x] 6. Implement RBAC permission system






  - [x] 6.1 Create PermissionChecker with role-permission mapping

    - _Requirements: Design - Components (RBAC Permission Checker)_

  - [x] 6.2 Implement require_permission decorator for route protection

    - _Requirements: Design - Components (RBAC Permission Checker)_
  - [x] 6.3 Write property test for RBAC enforcement









    - **Property 6: Role-Based Access Control Enforcement**
    - **Validates: Design - Property 6**

- [x] 7. Create authentication API endpoints
  - [x] 7.1 Implement POST /api/auth/register for tenant registration
    - _Requirements: Design - API Endpoints (Auth module)_
  - [ ]* 7.2 Write property test for tenant slug uniqueness
    - **Property 3: Tenant Slug Uniqueness**
    - **Validates: Design - Property 3**
  - [x] 7.3 Implement POST /api/auth/login with credential validation
    - _Requirements: Design - API Endpoints (Auth module)_
  - [x] 7.4 Implement POST /api/auth/refresh for token refresh
    - _Requirements: Design - API Endpoints (Auth module)_
  - [x] 7.5 Implement GET /api/auth/me for current user profile

    - _Requirements: Design - API Endpoints (Auth module)_

- [x] 8. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.

## Phase 3: Core Entity Management

- [x] 9. Implement student management





  - [x] 9.1 Create StudentRepository extending TenantAwareRepository


    - _Requirements: Design - Data Models (STUDENTS), Components (Base Repository)_

  - [x] 9.2 Create StudentService with business logic for CRUD operations

    - _Requirements: Design - API Endpoints (Students module)_

  - [x] 9.3 Create Pydantic schemas for student create/update/response

    - _Requirements: Design - Pydantic Schemas (StudentCreate, StudentResponse)_

  - [x] 9.4 Implement student API endpoints (GET, POST, PUT, DELETE /api/students)

    - _Requirements: Design - API Endpoints (Students module)_

  - [x] 9.5 Implement GET /api/students/{id} with profile aggregation (attendance, grades, fees)

    - _Requirements: Design - API Endpoints (Students module)_
  - [x] 9.6 Write property test for entity creation tenant association














    - **Property 7: Entity Creation Tenant Association**
    - **Validates: Design - Property 7**
  - [x] 9.7 Write property test for soft delete preservation






    - **Property 8: Soft Delete Preservation**
    - **Validates: Design - Property 8**
  - [x] 9.8 Write property test for filtered query result matching





    - **Property 18: Filtered Query Result Matching**
    - **Validates: Design - Property 18**

- [x] 10. Implement teacher management






  - [x] 10.1 Create TeacherRepository and TeacherService

    - _Requirements: Design - Data Models (TEACHERS), API Endpoints (Teachers module)_

  - [x] 10.2 Create Pydantic schemas for teacher operations

    - _Requirements: Design - Pydantic Schemas_

  - [x] 10.3 Implement teacher API endpoints (GET, POST, PUT /api/teachers)

    - _Requirements: Design - API Endpoints (Teachers module)_

  - [x] 10.4 Implement GET /api/teachers/{id}/classes for assigned classes

    - _Requirements: Design - API Endpoints (Teachers module)_

- [x] 11. Implement class and section management















  - [x] 11.1 Create ClassRepository, SectionRepository, SubjectRepository



    - _Requirements: Design - Data Models (CLASSES, SECTIONS, SUBJECTS)_

  - [x] 11.2 Create services for class, section, subject management



    - _Requirements: Design - API Endpoints (Classes, Sections modules)_

  - [x] 11.3 Implement class API endpoints with section management


    - _Requirements: Design - API Endpoints (Classes, Sections modules)_

  - [x] 11.4 Implement GET /api/classes/{id}/students for enrolled students




    - _Requirements: Design - API Endpoints (Classes module)_

- [x] 12. Checkpoint - Ensure all tests pass






  - Ensure all tests pass, ask the user if questions arise.

## Phase 4: Academic Features

- [x] 13. Implement attendance management










  - [x] 13.1 Create AttendanceRepository and AttendanceService



    - _Requirements: Design - Data Models (ATTENDANCE), API Endpoints (Attendance module)_

  - [x] 13.2 Implement POST /api/attendance/mark for bulk attendance marking
    - _Requirements: Design - API Endpoints (Attendance module)_
  - [x] 13.3 Write property test for bulk attendance recording






    - **Property 9: Bulk Attendance Recording**
    - **Validates: Design - Property 9**
  - [x] 13.4 Implement GET /api/attendance with filtering by class/date/student

    - _Requirements: Design - API Endpoints (Attendance module)_

  - [x] 13.5 Implement attendance percentage calculation in service
    - _Requirements: Design - Property 10 (calculation formula)_
  - [x] 13.6 Write property test for attendance percentage calculation






    - **Property 10: Attendance Percentage Calculation**
    - **Validates: Design - Property 10**
  - [x] 13.7 Implement GET /api/attendance/report for attendance reports

    - _Requirements: Design - API Endpoints (Reports module)_

- [x] 14. Implement grade and examination management







  - [x] 14.1 Create ExamRepository, GradeRepository and services

    - _Requirements: Design - Data Models (EXAMS, GRADES), API Endpoints (Grades module)_
  - [x] 14.2 Implement exam API endpoints (CRUD)

    - _Requirements: Design - API Endpoints (Grades module)_

  - [x] 14.3 Implement grade entry API with automatic grade letter calculation

    - _Requirements: Design - Property 11 (grade calculation)_
  - [x] 14.4 Write property test for grade calculation consistency






    - **Property 11: Grade Calculation Consistency**
    - **Validates: Design - Property 11**

  - [x] 14.5 Implement GET /api/grades/report-card/{student_id} for report card generation

    - _Requirements: Design - API Endpoints (Grades module)_

  - [x] 14.6 Implement grade analytics endpoint

    - _Requirements: Design - API Endpoints (Reports module)_

- [x] 15. Implement timetable management








  - [x] 15.1 Create TimetableRepository and TimetableService with conflict detection



    - _Requirements: Design - Data Models (TIMETABLE), Property 13_

  - [x] 15.2 Implement timetable API endpoints (CRUD)

    - _Requirements: Design - API Endpoints (Timetable module)_
  - [x] 15.3 Write property test for timetable conflict detection






    - **Property 13: Timetable Conflict Detection**
    - **Validates: Design - Property 13**


  - [x] 15.4 Implement GET /api/timetable with class/teacher filtering

    - _Requirements: Design - API Endpoints (Timetable module)_

- [x] 16. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.

## Phase 5: Financial & Communication

- [x] 17. Implement fee management











  - [x] 17.1 Create FeeRepository and FeeService

    - _Requirements: Design - Data Models (FEES), API Endpoints (Fees module)_

  - [x] 17.2 Implement fee API endpoints (GET, POST /api/fees)

    - _Requirements: Design - API Endpoints (Fees module)_

  - [x] 17.3 Implement POST /api/fees/{id}/payment with status update logic
    - _Requirements: Design - Property 12 (fee status logic)_
  - [x] 17.4 Write property test for fee payment status update






    - **Property 12: Fee Payment Status Update**
    - **Validates: Design - Property 12**
  - [x] 17.5 Implement GET /api/fees/pending for pending fees list

    - _Requirements: Design - API Endpoints (Fees module)_

  - [x] 17.6 Implement GET /api/fees/report for fee collection report



    - _Requirements: Design - API Endpoints (Reports module)_

- [ ] 18. Implement announcements and leave requests
























  - [x] 18.1 Create AnnouncementRepository and AnnouncementService







    - _Requirements: Design - Data Models (ANNOUNCEMENTS), API Endpoints (Announcements module)_

  - [x] 18.2 Implement announcement API endpoints with role-based filtering



    - _Requirements: Design - Property 14 (role filtering)_
  - [x] 18.3 Write property test for announcement role filtering







    - **Property 14: Announcement Role Filtering**
    - **Validates: Design - Property 14**

  - [x] 18.4 Create LeaveRequestRepository and LeaveRequestService

    - _Requirements: Design - Data Models (LEAVE_REQUESTS)_
  - [x] 18.5 Implement leave request API endpoints with approval workflow









































    - _Requirements: Design - API Endpoints_

- [x] 19. Implement reporting endpoints





  - [x] 19.1 Create ReportService for aggregating report data


    - _Requirements: Design - API Endpoints (Reports module)_
  - [x] 19.2 Implement GET /api/reports/attendance-summary


    - _Requirements: Design - API Endpoints (Reports module)_
  - [x] 19.3 Implement GET /api/reports/grade-analysis


    - _Requirements: Design - API Endpoints (Reports module)_
  - [x] 19.4 Implement GET /api/reports/fee-collection


    - _Requirements: Design - API Endpoints (Reports module)_

  - [x] 19.5 Implement PDF/CSV export functionality

    - _Requirements: Design - API Endpoints (Reports module)_

- [x] 20. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.

## Phase 6: Background Tasks & Caching

- [x] 21. Set up Celery and Redis integration






  - [x] 21.1 Configure Celery with Redis broker and result backend

    - _Requirements: Design - Architecture (Celery Workers)_

  - [x] 21.2 Create celery_worker.py entry point

    - _Requirements: Design - Architecture (Celery Workers)_

  - [x] 21.3 Configure Flower for task monitoring

    - _Requirements: Design - Architecture (Flower Monitor)_

- [x] 22. Implement background tasks






  - [x] 22.1 Create task for bulk email notifications with tenant context

    - _Requirements: Design - Architecture (Celery Workers)_

  - [x] 22.2 Create task for PDF report generation

    - _Requirements: Design - API Endpoints (Reports module)_
  - [x] 22.3 Create task for CSV bulk import with progress tracking


    - _Requirements: Design - Architecture (Celery Workers)_

- [x] 23. Implement caching layer







  - [x] 23.1 Add Redis caching to frequently accessed queries (class lists, teacher schedules)

    - _Requirements: Design - Components (Cache Service)_
  - [x] 23.2 Write property test for pagination bounds






    - **Property 15: Pagination Bounds**
    - **Validates: Design - Property 15**


  - [x] 23.3 Implement cache invalidation on entity updates

    - _Requirements: Design - Property 16_
  - [x] 23.4 Write property test for cache invalidation on update






    - **Property 16: Cache Invalidation on Update**
    - **Validates: Design - Property 16**

- [x] 24. Implement audit logging







  - [x] 24.1 Create AuditLog model and repository


    - _Requirements: Design - Property 17_


  - [x] 24.2 Implement audit logging middleware/decorator for sensitive operations


    - _Requirements: Design - Property 17_
  - [x] 24.3 Write property test for audit log completeness












    - **Property 17: Audit Log Completeness**
    - **Validates: Design - Property 17**

- [x] 25. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.

## Phase 7: Frontend Foundation

- [x] 26. Set up Next.js frontend project




  - [x] 26.1 Initialize Next.js 14+ project with App Router and TypeScript

    - _Requirements: Design - Architecture (Client Layer)_

  - [x] 26.2 Configure Tailwind CSS

    - _Requirements: Design - Architecture (Client Layer)_
  - [x] 26.3 Install and configure shadcn/ui components

    - _Requirements: Design - Architecture (Client Layer)_

  - [x] 26.4 Create directory structure: app/(auth), app/(dashboard), components, context, lib


    - _Requirements: Design - Frontend Components_

- [-] 27. Implement context providers and API client









  - [x] 27.1 Create API client with token management and error handling


    - _Requirements: Design - Frontend Components (API Client)_
  - [x] 27.2 Implement AuthContext with login, logout, token refresh


    - _Requirements: Design - Frontend Components (Auth Context)_


  - [x] 27.3 Implement TenantContext for tenant settings

    - _Requirements: Design - Frontend Components (Tenant Context)_

  - [x] 27.4 Create protected route wrapper component

    - _Requirements: Design - Property 6 (RBAC)_

- [x] 28. Create layout and navigation components






  - [x] 28.1 Create responsive sidebar navigation with role-based menu items

    - _Requirements: Design - Property 6 (RBAC)_

  - [x] 28.2 Create top navbar with tenant name, user profile, notifications

    - _Requirements: Design - Frontend Components_

  - [x] 28.3 Create dashboard layout wrapper

    - _Requirements: Design - Frontend Components_

  - [x] 28.4 Implement toast notification system

    - _Requirements: Design - Error Handling (Frontend)_

  - [x] 28.5 Create confirmation dialog component

    - _Requirements: Design - Error Handling (Frontend)_

- [x] 29. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.

## Phase 8: Frontend Pages - Auth & Dashboard

- [x] 30. Implement authentication pages





  - [x] 30.1 Create login page with form validation






    - _Requirements: Design - API Endpoints (Auth module)_
  - [x] 30.2 Create tenant registration page

    - _Requirements: Design - API Endpoints (Auth module)_

  - [x] 30.3 Implement auth redirect logic

    - _Requirements: Design - Frontend Components (Auth Context)_

- [x] 31. Implement dashboard home page















  - [x] 31.1 Create dashboard overview with role-based cards (total students, teachers, pending fees)

    - _Requirements: Design - Property 6 (RBAC)_



  - [x] 31.2 Display recent announcements widget

    - _Requirements: Design - API Endpoints (Announcements module)_

  - [x] 31.3 Create quick actions based on user role
    - _Requirements: Design - Property 6 (RBAC)_

## Phase 9: Frontend Pages - Core Modules

- [x] 32. Implement student management pages






  - [x] 32.1 Create student list page with search, filters, pagination

    - _Requirements: Design - Property 15 (Pagination), Property 18 (Filtering)_

  - [x] 32.2 Create add/edit student form with validation

    - _Requirements: Design - Pydantic Schemas (StudentCreate)_

  - [x] 32.3 Create student profile page with tabs (info, attendance, grades, fees)

    - _Requirements: Design - API Endpoints (Students module)_
  - [x] 32.4 Implement student delete with confirmation


    - _Requirements: Design - Property 8 (Soft Delete)_

- [x] 33. Implement teacher management pages










  - [x] 33.1 Create teacher list page with search and filters

    - _Requirements: Design - Property 18 (Filtering)_

  - [x] 33.2 Create add/edit teacher form



    - _Requirements: Design - Pydantic Schemas_
  - [x] 33.3 Create teacher profile page with assigned classes and schedule


    - _Requirements: Design - API Endpoints (Teachers module)_

- [x] 34. Implement class and section pages






  - [x] 34.1 Create class list page

    - _Requirements: Design - API Endpoints (Classes module)_



  - [x] 34.2 Create add/edit class form with section management

    - _Requirements: Design - Data Models (CLASSES, SECTIONS)_
  - [x] 34.3 Create class detail page with enrolled students


    - _Requirements: Design - API Endpoints (Classes module)_

- [x] 35. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.

## Phase 10: Frontend Pages - Academic Features

- [x] 36. Implement attendance pages









  - [x] 36.1 Create attendance marking page with class/section selector and grid view

    - _Requirements: Design - Property 9 (Bulk Attendance)_

  - [x] 36.2 Create attendance history page with date picker and filters

    - _Requirements: Design - Property 18 (Filtering)_

  - [x] 36.3 Create attendance report page with charts

    - _Requirements: Design - Property 10 (Attendance Percentage)_

- [x] 37. Implement grades pages

























  - [x] 37.1 Create exam management page

    - _Requirements: Design - Data Models (EXAMS)_
  - [x] 37.2 Create grade entry form by class/exam

    - _Requirements: Design - Property 11 (Grade Calculation)_







  - [x] 37.3 Create report card view page

    - _Requirements: Design - API Endpoints (Grades module)_

  - [x] 37.4 Create grade analytics page with charts

    - _Requirements: Design - API Endpoints (Reports module)_

- [x] 38. Implement timetable pages















  - [x] 38.1 Create timetable view with visual grid (class-wise and teacher-wise)


    - _Requirements: Design - Data Models (TIMETABLE)_

  - [x] 38.2 Create timetable entry form with conflict validation

    - _Requirements: Design - Property 13 (Conflict Detection)_

## Phase 11: Frontend Pages - Financial & Communication

- [-] 39. Implement fee management pages




  - [x] 39.1 Create fee list page with pending fees highlight

    - _Requirements: Design - Property 12 (Fee Status)_

  - [x] 39.2 Create fee creation form

    - _Requirements: Design - Pydantic Schemas (FeeCreate)_

  - [x] 39.3 Create payment recording form

    - _Requirements: Design - Pydantic Schemas (PaymentRecord)_
  - [x] 39.4 Create fee collection report page






    - _Requirements: Design - API Endpoints (Reports module)_

- [x] 40. Implement announcement and leave request pages






  - [x] 40.1 Create announcement list and create/edit pages

    - _Requirements: Design - Property 14 (Role Filtering)_

  - [x] 40.2 Create leave request submission page

    - _Requirements: Design - Data Models (LEAVE_REQUESTS)_

  - [x] 40.3 Create leave request approval page for admins

    - _Requirements: Design - Property 6 (RBAC)_

- [x] 41. Implement reports pages






  - [x] 41.1 Create reports dashboard with report type selection

    - _Requirements: Design - API Endpoints (Reports module)_

  - [x] 41.2 Implement report export functionality (PDF/CSV download)

    - _Requirements: Design - API Endpoints (Reports module)_

- [x] 42. Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.

## Phase 12: Super Admin Dashboard

- [x] 43. Set up admin dashboard






  - [x] 43.1 Create separate admin app layout with super admin navigation

    - _Requirements: Design - Architecture (Admin Dashboard)_


  - [x] 43.2 Implement super admin authentication check





    - _Requirements: Design - Property 6 (RBAC)_

- [x] 44. Implement tenant management






  - [x] 44.1 Create tenant list page with status and subscription info

    - _Requirements: Design - Data Models (TENANTS)_

  - [x] 44.2 Create tenant detail page with usage statistics

    - _Requirements: Design - Data Models (TENANTS)_

  - [x] 44.3 Create tenant configuration form

    - _Requirements: Design - Data Models (TENANTS - settings field)_

- [x] 45. Implement subscription management









  - [x] 45.1 Create subscription plans management page

    - _Requirements: Design - Data Models (TENANTS - subscription_plan)_

  - [x] 45.2 Create billing history page

    - _Requirements: Design - Data Models (TENANTS)_

- [x] 46. Implement platform analytics






  - [x] 46.1 Create analytics dashboard with total users, revenue, growth metrics

    - _Requirements: Design - Architecture (Admin Dashboard)_

  - [x] 46.2 Create usage charts and graphs

    - _Requirements: Design - Architecture (Admin Dashboard)_

## Phase 13: Security & Polish

- [x] 47. Implement security features






  - [x] 47.1 Add rate limiting middleware to API endpoints

    - _Requirements: Design - Architecture (Rate Limiter)_

  - [x] 47.2 Implement input sanitization for XSS prevention

    - _Requirements: Design - Error Handling_

  - [x] 47.3 Add CSRF token validation for form submissions

    - _Requirements: Design - Error Handling_

- [x] 48. Final integration and polish













  - [x] 48.1 Add loading states and skeleton screens to all pages

    - _Requirements: Design - Error Handling (Frontend)_

  - [x] 48.2 Ensure responsive design works on mobile/tablet/desktop

    - _Requirements: Design - Frontend Components_


  - [x] 48.3 Add error boundaries and fallback UI

    - _Requirements: Design - Error Handling (Frontend)_

- [x] 49. Final Checkpoint - Ensure all tests pass





  - Ensure all tests pass, ask the user if questions arise.
