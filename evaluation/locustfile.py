from locust import HttpUser, between, task
import time
import uuid


class ComplianceUser(HttpUser):
    wait_time = between(0.2, 1.0)

    @task
    def submit_and_poll_complete_run(self):
        proposal = {
            "building_use": "residential",
            "plot_area": 200,
            "road_width": 6,
            "proposed_height": 9,
            "zone": "A - intensely developed area",
            "site_width": 10,
            "site_depth": 20,
        }
        correlation_id = str(uuid.uuid4())
        started = time.perf_counter()
        with self.client.post(
            "/runs",
            json=proposal,
            headers={"X-Correlation-ID": correlation_id},
            name="/runs",
            catch_response=True,
        ) as response:
            if response.status_code != 202:
                response.failure(f"submission returned {response.status_code}")
                self._record_workflow(started, False, correlation_id)
                return
            try:
                run_id = response.json()["run_id"]
            except Exception:
                response.failure("submission did not include run_id")
                self._record_workflow(started, False, correlation_id)
                return
            response.success()

        deadline = time.perf_counter() + 60
        while time.perf_counter() < deadline:
            result = self.client.get(f"/runs/{run_id}", name="/runs/{run_id}")
            if result.status_code != 200:
                self._record_workflow(started, False, correlation_id)
                return
            status = result.json().get("status")
            if status in {"completed", "failed"}:
                self._record_workflow(started, status == "completed", correlation_id)
                return
            time.sleep(0.5)
        self._record_workflow(started, False, correlation_id)

    def _record_workflow(self, started, success, correlation_id):
        self.environment.events.request.fire(
            request_type="WORKFLOW",
            name="submit_to_terminal_result",
            response_time=(time.perf_counter() - started) * 1000,
            response_length=0,
            exception=None if success else TimeoutError(
                "run did not reach a successful terminal state within 60s"
            ),
            context={"correlation_id": correlation_id},
        )
