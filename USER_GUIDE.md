# ACG-ThreadView — User Guide

**Version 1.0** | © Application Consulting Group, Inc.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Getting Started](#2-getting-started)
3. [Setting Up a Connection](#3-setting-up-a-connection)
   - 3.1 [On-Premises TM1 (v11)](#31-on-premises-tm1-v11)
   - 3.2 [Planning Analytics on Cloud (PAoC)](#32-planning-analytics-on-cloud-paoc)
   - 3.3 [Planning Analytics SaaS (v12)](#33-planning-analytics-saas-v12)
4. [Starting a Monitoring Session](#4-starting-a-monitoring-session)
5. [Reading the Thread Table](#5-reading-the-thread-table)
6. [Cancelling a Thread](#6-cancelling-a-thread)
7. [Adjusting the Refresh Rate](#7-adjusting-the-refresh-rate)
8. [Managing Connections](#8-managing-connections)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Overview

ACG-ThreadView connects to an IBM Planning Analytics / TM1 server and displays all active threads in real time. It is intended for system administrators and developers who need to:

- Identify long-running or stuck processes
- Monitor lock contention (write, read, and intent-exclusive locks)
- Cancel runaway threads without restarting the server

The application polls the server's REST API at a configurable interval and refreshes the thread table automatically.

---

## 2. Getting Started

### Running from the executable

1. Copy `ACG-ThreadView.exe` and the `config/` folder to the same directory.
2. Double-click `ACG-ThreadView.exe`.
3. The main window opens. No installation is required.

### Running from source

```bash
pip install -r requirements.txt
python src/main.py
```

---

## 3. Setting Up a Connection

Open the connection editor via **Setup → Setup Connection** in the menu bar.

> All connections are saved to `config/connections.json` next to the executable and persist between sessions.

### 3.1 On-Premises TM1 (v11)

Use this type for TM1 servers hosted on your own infrastructure.

| Field            | Description                                                                                      |
|------------------|--------------------------------------------------------------------------------------------------|
| **Name**         | A unique label for this connection (e.g. `PROD`, `DEV`).                                         |
| **Cloud Type**   | Select **On-Prem**.                                                                              |
| **Address**      | Hostname or IP address of the TM1 server (e.g. `tm1server.corp.local`).                         |
| **Port**         | `HTTPPortNumber` from `Tm1s.cfg`. Default is `8010`.                                             |
| **Instance**     | TM1 instance name (e.g. `Planning`).                                                             |
| **SSL**          | Check if the server uses HTTPS (`SSLCertificateID` is set in `Tm1s.cfg`).                        |
| **Security**     | Authentication mode — see the table below.                                                       |

#### Security Modes

| Mode        | When to Use                                        | Additional Fields Required                  |
|-------------|-----------------------------------------------------|---------------------------------------------|
| **Standard**| Username and password defined in TM1.              | _(none)_                                    |
| **CAM**     | Corporate LDAP / Active Directory via CAM.         | **CAM Namespace ID** (from CAM config).     |
| **CAM SSO** | Single sign-on via CAM using a gateway service.    | **CAM Namespace ID** + **SSO Gateway URL**. |

**Example — Standard on-prem connection:**

```
Name:     PROD
Type:     On-Prem
Address:  tm1prod.corp.local
Port:     12370
Instance: Planning
SSL:      ✓
Security: Standard
```

---

### 3.2 Planning Analytics on Cloud (PAoC)

Use this type for IBM-hosted PAoC environments.

| Field          | Description                                                                 |
|----------------|-----------------------------------------------------------------------------|
| **Name**       | A unique label for this connection (e.g. `WakeProd`).                       |
| **Cloud Type** | Select **PAoC**.                                                            |
| **Address**    | PAoC hostname (e.g. `mycompany.planning-analytics.cloud.ibm.com`).          |
| **Instance**   | TM1 instance / database name as shown in the PAoC portal.                  |

At login you will be prompted for your **IBM ID username** and **password**.

**Example:**

```
Name:     WakeProd
Type:     PAoC
Address:  wfcprod.planning-analytics.cloud.ibm.com
Instance: Planning
```

---

### 3.3 Planning Analytics SaaS (v12)

Use this type for fully-managed IBM Planning Analytics SaaS (v12) tenants.

| Field          | Description                                                                          |
|----------------|--------------------------------------------------------------------------------------|
| **Name**       | A unique label for this connection (e.g. `SaasProd`).                                |
| **Cloud Type** | Select **PA SaaS**.                                                                  |
| **Address**    | SaaS regional endpoint (e.g. `us-east-1.planninganalytics.saas.ibm.com`).           |
| **Instance**   | TM1 database/instance name.                                                          |
| **Tenant ID**  | Your tenant ID from the IBM Cloud portal (e.g. `CY9YMZKP7MLX`).                     |

At login you will be prompted for an **API key** (generated in the IBM Cloud IAM console).

**Example:**

```
Name:      SaasProd
Type:      PA SaaS
Address:   us-east-1.planninganalytics.saas.ibm.com
Instance:  Planning
Tenant ID: CY9YMZKP7MLX
```

---

## 4. Starting a Monitoring Session

1. Select a connection from the **Connection** drop-down at the bottom of the main window.
2. Click **Start**.
3. Enter your credentials when prompted:
   - **On-Prem / PAoC** — username and password.
   - **PA SaaS** — API key.
4. The thread table populates and refreshes automatically at the configured interval.
5. The status bar shows the number of threads and the last refresh timestamp.

To stop monitoring, click **Stop**. This closes the connection and clears the table.

---

## 5. Reading the Thread Table

Each row represents one active (non-idle) thread on the server. The table updates every N seconds as set by the **Refresh (s)** control.

| Column           | Description                                                                  |
|------------------|------------------------------------------------------------------------------|
| **ID**           | Unique numeric thread identifier assigned by TM1.                            |
| **Name**         | Thread name (usually the connected user or service account).                 |
| **State**        | Current thread state — `Run` (executing) or `Wait` (blocked on a lock).     |
| **Type**         | `User` (client request) or `System` (background process).                   |
| **Function**     | REST endpoint or TM1 function being executed (truncated if long).            |
| **Wait (sec.)**  | Seconds the thread has spent waiting for a lock. `0` means not blocked.      |
| **Elapsed (sec.)** | Total seconds since the thread started.                                    |
| **W/R/Ix locks** | Lock counts in `Write/Read/Intent-exclusive` format (e.g. `0/4/0`).         |
| **Context**      | Connection context (e.g. `Workspace`, `Client`).                             |
| **Info**         | Additional detail string provided by TM1.                                    |
| **Object name**  | Name of the cube, dimension, process, or other object being accessed.        |
| **Object type**  | Type of that object (e.g. `Cube`, `Dimension`, `Process`).                   |

> **Tip — Identifying a stuck thread:**  A thread is likely stuck if its **State** is `Wait` and its **Wait (sec.)** value keeps growing with each refresh.

> **Tip — Lock contention:** A high **W** (write) lock count on one thread combined with other threads in `Wait` state usually indicates lock contention on a shared object.

---

## 6. Cancelling a Thread

1. Right-click the thread row you want to cancel.
2. Select **Cancel thread {ID}** from the context menu.
3. A confirmation dialog appears — click **Yes** to proceed.
4. The application sends a cancel request to the server and immediately refreshes the table.

> **Warning:** Cancelling a thread aborts the operation in progress (e.g. a running TI process or a long MDX query). Unsaved data in that thread will be lost. Use with caution in production environments.

---

## 7. Adjusting the Refresh Rate

The **Refresh (s)** spinner at the bottom of the main window controls how often the server is polled.

- Range: **5 – 300 seconds**
- Default: **30 seconds**
- The new interval takes effect immediately — no need to stop and restart monitoring.

> For busy production servers, a longer interval (30–60 seconds) reduces load. For active troubleshooting, 5–10 seconds gives near-real-time visibility.

---

## 8. Managing Connections

Open **Setup → Setup Connection** to manage saved connections.

| Action         | How to do it                                                                                   |
|----------------|------------------------------------------------------------------------------------------------|
| **Add**        | Fill in all fields and click **Save**.                                                         |
| **Edit**       | Select a connection from the list, modify the fields, and click **Save**.                      |
| **Delete**     | Select a connection and click **Delete**, then confirm.                                        |
| **Rename**     | Edit the **Name** field of an existing connection and click **Save**.                          |

Connection profiles are stored in `config/connections.json` next to the executable. You can back up or copy this file to share connection profiles with colleagues.

---

## 9. Troubleshooting

### The application cannot connect

- **On-Prem:** Verify the address, port, and instance name. Check that `HTTPPortNumber` in `Tm1s.cfg` matches. Try toggling SSL if the connection fails with a certificate error.
- **PAoC / PA SaaS:** Verify that your IBM ID / API key has access to the instance.
- **Firewall:** Ensure the machine running ACG-ThreadView can reach the TM1 server on the configured port.

### SSL certificate errors

If you see an SSL error on an On-Prem connection:
- Make sure the **SSL** checkbox matches the server configuration (both must be enabled or both disabled).
- If the server uses a self-signed certificate, you may need to add it to your system's trusted certificate store.

### The thread table is empty after connecting

- The server may have no active (non-idle) threads at that moment — this is normal.
- Verify the user account has sufficient administrative privileges to view all threads on the TM1 server.

### Wait/Elapsed columns show no values

- Older on-prem TM1 versions may not return timing data in the REST API. This is a server-side limitation.

### Thread cancel fails

- Ensure the connecting user has `ADMIN` privileges on the TM1 server.
- The thread may have already completed by the time the cancel request arrived.

---

*For technical issues or feature requests, contact the ACG development team.*
