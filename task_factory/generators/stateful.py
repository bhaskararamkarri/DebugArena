"""Category D: State Management & Lifecycle Task Generator."""

from __future__ import annotations

from typing import Any, Dict
from task_factory.generators.base import BaseGenerator


class StatefulTaskGenerator(BaseGenerator):
    """Generates complex stateful and multi-step lifecycle tasks (sagas, FSMs, transaction rollbacks)."""

    def generate(self, spec: Dict[str, Any], seed: int = 42) -> Dict[str, Any]:
        task_id = spec.get("task_id", "v24_order_processing_saga_rollback")
        sub_type = spec.get("sub_type", "saga")

        if sub_type == "event_sourcing" or "event_sourcing" in task_id:
            return self._generate_event_sourcing(task_id, spec, seed)
        elif sub_type == "websocket_fsm" or "websocket" in task_id:
            return self._generate_websocket_fsm(task_id, spec, seed)
        elif sub_type == "compensating_nesting" or "compensat" in task_id:
            return self._generate_compensating_nesting(task_id, spec, seed)
        elif task_id == "v43_saga_distributed_orchestrator" or sub_type == "cloud_saga":
            return self._generate_cloud_provisioning_saga(task_id, spec, seed)
        elif sub_type == "two_phase_commit" or "two_phase" in task_id or "2pc" in task_id or "crash_recovery" in task_id:
            return self._generate_two_phase_commit(task_id, spec, seed)
        elif sub_type == "crdt" or "crdt" in task_id or "convergence" in task_id:
            return self._generate_crdt_convergence(task_id, spec, seed)
        return self._generate_saga_coordinator(task_id, spec, seed)

    def _generate_saga_coordinator(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "order_models.py": (
                '"""Order and transaction state definitions."""\n\n'
                'from dataclasses import dataclass, field\n'
                'from typing import List, Optional\n\n\n'
                '@dataclass\n'
                'class OrderItem:\n'
                '    sku: str\n'
                '    quantity: int\n'
                '    unit_price: float\n\n\n'
                '@dataclass\n'
                'class OrderContext:\n'
                '    order_id: str\n'
                '    customer_id: str\n'
                '    items: List[OrderItem]\n'
                '    total_amount: float\n'
                '    status: str = "PENDING"\n'
                '    compensation_log: List[str] = field(default_factory=list)\n'
            ),
            "inventory_service.py": (
                '"""Inventory reservation and release service."""\n\n'
                'from typing import Dict\n'
                'from order_models import OrderItem\n\n\n'
                'class InventoryService:\n'
                '    def __init__(self, initial_stock: Dict[str, int]):\n'
                '        self.stock = dict(initial_stock)\n'
                '        self.reservations: dict[str, list[OrderItem]] = {}\n\n'
                '    def reserve(self, order_id: str, items: list[OrderItem]) -> bool:\n'
                '        for it in items:\n'
                '            if self.stock.get(it.sku, 0) < it.quantity:\n'
                '                return False\n'
                '        for it in items:\n'
                '            self.stock[it.sku] -= it.quantity\n'
                '        self.reservations[order_id] = items\n'
                '        return True\n\n'
                '    def cancel_reservation(self, order_id: str) -> None:\n'
                '        # BUG: Fails to remove order_id from reservations dictionary,\n'
                '        # causing duplicate refunding or dirty state on subsequent calls\n'
                '        items = self.reservations.get(order_id, [])\n'
                '        for it in items:\n'
                '            self.stock[it.sku] = self.stock.get(it.sku, 0) + it.quantity\n'
            ),
            "payment_service.py": (
                '"""Payment gateway authorization service."""\n\n'
                'from typing import Set\n\n\n'
                'class PaymentService:\n'
                '    def __init__(self, authorized_cards: Set[str]):\n'
                '        self.authorized_cards = authorized_cards\n'
                '        self.processed_payments: dict[str, float] = {}\n\n'
                '    def charge(self, order_id: str, card_token: str, amount: float) -> bool:\n'
                '        if card_token not in self.authorized_cards:\n'
                '            return False\n'
                '        self.processed_payments[order_id] = amount\n'
                '        return True\n\n'
                '    def refund(self, order_id: str) -> bool:\n'
                '        if order_id in self.processed_payments:\n'
                '            del self.processed_payments[order_id]\n'
                '            return True\n'
                '        return False\n'
            ),
            "shipping_service.py": (
                '"""Shipping fulfillment provider."""\n\n'
                'class ShippingService:\n'
                '    def __init__(self):\n'
                '        self.dispatches: dict[str, str] = {}\n\n'
                '    def book_shipment(self, order_id: str, address: str) -> bool:\n'
                '        if not address:\n'
                '            return False\n'
                '        self.dispatches[order_id] = address\n'
                '        return True\n\n'
                '    def cancel_shipment(self, order_id: str) -> bool:\n'
                '        if order_id in self.dispatches:\n'
                '            del self.dispatches[order_id]\n'
                '            return True\n'
                '        return False\n'
            ),
            "saga_coordinator.py": (
                '"""Distributed Saga orchestrator for atomic multi-service order processing."""\n\n'
                'from order_models import OrderContext\n'
                'from inventory_service import InventoryService\n'
                'from payment_service import PaymentService\n'
                'from shipping_service import ShippingService\n\n\n'
                'class OrderSagaCoordinator:\n'
                '    def __init__(\n'
                '        self,\n'
                '        inventory: InventoryService,\n'
                '        payment: PaymentService,\n'
                '        shipping: ShippingService,\n'
                '    ):\n'
                '        self.inventory = inventory\n'
                '        self.payment = payment\n'
                '        self.shipping = shipping\n\n'
                '    def execute_order(\n'
                '        self,\n'
                '        ctx: OrderContext,\n'
                '        card_token: str,\n'
                '        shipping_address: str,\n'
                '    ) -> bool:\n'
                '        # Step 1: Inventory Reservation\n'
                '        if not self.inventory.reserve(ctx.order_id, ctx.items):\n'
                '            ctx.status = "FAILED_INSUFFICIENT_STOCK"\n'
                '            return False\n\n'
                '        # Step 2: Payment Authorization\n'
                '        if not self.payment.charge(ctx.order_id, card_token, ctx.total_amount):\n'
                '            # BUG: Rollback order is incorrect and fails to update ctx.status to "ROLLED_BACK"\n'
                '            # Also fails to log compensation step in ctx.compensation_log\n'
                '            self.inventory.cancel_reservation(ctx.order_id)\n'
                '            ctx.status = "FAILED_PAYMENT_DECLINED"\n'
                '            return False\n\n'
                '        # Step 3: Shipping Booking\n'
                '        if not self.shipping.book_shipment(ctx.order_id, shipping_address):\n'
                '            # BUG: When shipping fails, only refund is called, forgetting inventory release!\n'
                '            self.payment.refund(ctx.order_id)\n'
                '            ctx.status = "FAILED_SHIPPING"\n'
                '            return False\n\n'
                '        ctx.status = "COMPLETED"\n'
                '        return True\n'
            ),
        }

        reference_fix = {
            "inventory_service.py": (
                '"""Inventory reservation and release service."""\n\n'
                'from typing import Dict\n'
                'from order_models import OrderItem\n\n\n'
                'class InventoryService:\n'
                '    def __init__(self, initial_stock: Dict[str, int]):\n'
                '        self.stock = dict(initial_stock)\n'
                '        self.reservations: dict[str, list[OrderItem]] = {}\n\n'
                '    def reserve(self, order_id: str, items: list[OrderItem]) -> bool:\n'
                '        for it in items:\n'
                '            if self.stock.get(it.sku, 0) < it.quantity:\n'
                '                return False\n'
                '        for it in items:\n'
                '            self.stock[it.sku] -= it.quantity\n'
                '        self.reservations[order_id] = items\n'
                '        return True\n\n'
                '    def cancel_reservation(self, order_id: str) -> None:\n'
                '        items = self.reservations.pop(order_id, [])\n'
                '        for it in items:\n'
                '            self.stock[it.sku] = self.stock.get(it.sku, 0) + it.quantity\n'
            ),
            "saga_coordinator.py": (
                '"""Distributed Saga orchestrator for atomic multi-service order processing."""\n\n'
                'from order_models import OrderContext\n'
                'from inventory_service import InventoryService\n'
                'from payment_service import PaymentService\n'
                'from shipping_service import ShippingService\n\n\n'
                'class OrderSagaCoordinator:\n'
                '    def __init__(\n'
                '        self,\n'
                '        inventory: InventoryService,\n'
                '        payment: PaymentService,\n'
                '        shipping: ShippingService,\n'
                '    ):\n'
                '        self.inventory = inventory\n'
                '        self.payment = payment\n'
                '        self.shipping = shipping\n\n'
                '    def execute_order(\n'
                '        self,\n'
                '        ctx: OrderContext,\n'
                '        card_token: str,\n'
                '        shipping_address: str,\n'
                '    ) -> bool:\n'
                '        # Step 1: Inventory Reservation\n'
                '        if not self.inventory.reserve(ctx.order_id, ctx.items):\n'
                '            ctx.status = "FAILED_INSUFFICIENT_STOCK"\n'
                '            return False\n\n'
                '        # Step 2: Payment Authorization\n'
                '        if not self.payment.charge(ctx.order_id, card_token, ctx.total_amount):\n'
                '            self.inventory.cancel_reservation(ctx.order_id)\n'
                '            ctx.compensation_log.append("INVENTORY_COMPENSATED")\n'
                '            ctx.status = "ROLLED_BACK_PAYMENT_DECLINED"\n'
                '            return False\n\n'
                '        # Step 3: Shipping Booking\n'
                '        if not self.shipping.book_shipment(ctx.order_id, shipping_address):\n'
                '            # Compensate in reverse order: shipping -> payment -> inventory\n'
                '            self.payment.refund(ctx.order_id)\n'
                '            ctx.compensation_log.append("PAYMENT_REFUNDED")\n'
                '            self.inventory.cancel_reservation(ctx.order_id)\n'
                '            ctx.compensation_log.append("INVENTORY_COMPENSATED")\n'
                '            ctx.status = "ROLLED_BACK_SHIPPING_FAILED"\n'
                '            return False\n\n'
                '        ctx.status = "COMPLETED"\n'
                '        return True\n'
            ),
        }

        tests = {
            "test_saga_coordinator.py": (
                'from order_models import OrderContext, OrderItem\n'
                'from inventory_service import InventoryService\n'
                'from payment_service import PaymentService\n'
                'from shipping_service import ShippingService\n'
                'from saga_coordinator import OrderSagaCoordinator\n\n\n'
                'def setup_services():\n'
                '    inv = InventoryService({"SKU_LAPTOP": 5, "SKU_MOUSE": 10})\n'
                '    pay = PaymentService({"card_valid_123"})\n'
                '    ship = ShippingService()\n'
                '    coord = OrderSagaCoordinator(inv, pay, ship)\n'
                '    return inv, pay, ship, coord\n\n\n'
                'def test_happy_path_order_completion():\n'
                '    inv, pay, ship, coord = setup_services()\n'
                '    ctx = OrderContext("ord_1", "cust_1", [OrderItem("SKU_LAPTOP", 2, 1000.0)], 2000.0)\n'
                '    res = coord.execute_order(ctx, "card_valid_123", "123 Tech Blvd")\n'
                '    assert res is True\n'
                '    assert ctx.status == "COMPLETED"\n'
                '    assert inv.stock["SKU_LAPTOP"] == 3\n'
                '    assert pay.processed_payments["ord_1"] == 2000.0\n'
                '    assert ship.dispatches["ord_1"] == "123 Tech Blvd"\n\n\n'
                'def test_insufficient_stock_fails_fast_without_side_effects():\n'
                '    inv, pay, ship, coord = setup_services()\n'
                '    ctx = OrderContext("ord_2", "cust_2", [OrderItem("SKU_LAPTOP", 10, 1000.0)], 10000.0)\n'
                '    res = coord.execute_order(ctx, "card_valid_123", "456 Oak Lane")\n'
                '    assert res is False\n'
                '    assert ctx.status == "FAILED_INSUFFICIENT_STOCK"\n'
                '    assert inv.stock["SKU_LAPTOP"] == 5\n'
                '    assert len(pay.processed_payments) == 0\n\n\n'
                'def test_payment_decline_compensates_inventory_fully():\n'
                '    inv, pay, ship, coord = setup_services()\n'
                '    ctx = OrderContext("ord_3", "cust_3", [OrderItem("SKU_MOUSE", 3, 25.0)], 75.0)\n'
                '    # Card is declined\n'
                '    res = coord.execute_order(ctx, "card_declined_999", "789 Pine Rd")\n'
                '    assert res is False\n'
                '    assert ctx.status == "ROLLED_BACK_PAYMENT_DECLINED"\n'
                '    assert "INVENTORY_COMPENSATED" in ctx.compensation_log\n'
                '    # Stock restored back to initial\n'
                '    assert inv.stock["SKU_MOUSE"] == 10\n'
                '    assert "ord_3" not in inv.reservations\n\n\n'
                'def test_shipping_failure_compensates_payment_and_inventory():\n'
                '    inv, pay, ship, coord = setup_services()\n'
                '    ctx = OrderContext("ord_4", "cust_4", [OrderItem("SKU_LAPTOP", 1, 1000.0)], 1000.0)\n'
                '    # Empty shipping address triggers shipping failure\n'
                '    res = coord.execute_order(ctx, "card_valid_123", "")\n'
                '    assert res is False\n'
                '    assert ctx.status == "ROLLED_BACK_SHIPPING_FAILED"\n'
                '    assert ctx.compensation_log == ["PAYMENT_REFUNDED", "INVENTORY_COMPENSATED"]\n'
                '    assert inv.stock["SKU_LAPTOP"] == 5\n'
                '    assert "ord_4" not in pay.processed_payments\n\n\n'
                'def test_repeated_compensation_is_idempotent():\n'
                '    inv, pay, ship, coord = setup_services()\n'
                '    inv.reserve("ord_5", [OrderItem("SKU_LAPTOP", 1, 1000.0)])\n'
                '    assert inv.stock["SKU_LAPTOP"] == 4\n'
                '    inv.cancel_reservation("ord_5")\n'
                '    assert inv.stock["SKU_LAPTOP"] == 5\n'
                '    # Calling cancel_reservation again must not add surplus inventory\n'
                '    inv.cancel_reservation("ord_5")\n'
                '    assert inv.stock["SKU_LAPTOP"] == 5\n\n\n'
                'def test_multi_item_order_inventory_tracking():\n'
                '    inv, pay, ship, coord = setup_services()\n'
                '    items = [OrderItem("SKU_LAPTOP", 1, 1000.0), OrderItem("SKU_MOUSE", 2, 25.0)]\n'
                '    ctx = OrderContext("ord_6", "cust_6", items, 1050.0)\n'
                '    res = coord.execute_order(ctx, "card_valid_123", "Road 10")\n'
                '    assert res is True\n'
                '    assert inv.stock["SKU_LAPTOP"] == 4\n'
                '    assert inv.stock["SKU_MOUSE"] == 8\n\n\n'
                'def test_cancelled_order_leaves_no_lingering_reservations():\n'
                '    inv, pay, ship, coord = setup_services()\n'
                '    ctx = OrderContext("ord_7", "cust_7", [OrderItem("SKU_MOUSE", 5, 25.0)], 125.0)\n'
                '    coord.execute_order(ctx, "bad_card", "Road 11")\n'
                '    assert len(inv.reservations) == 0\n'
                '    assert inv.stock["SKU_MOUSE"] == 10\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "saga_distributed_transaction_rollback_omission",
            "categories": ["D", "E", "I"],
            "description": "Distributed saga coordinator fails to execute reverse compensation steps on shipping failure, leaving inventory and payment inconsistent.",
            "spec_notes": "OrderSagaCoordinator must execute compensations in reverse order on failure and update compensation_log.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 5,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "e-commerce",
            },
        }

    def _generate_event_sourcing(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "events.py": (
                '"""Domain event definitions."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any, Dict\n\n\n'
                '@dataclass\n'
                'class DomainEvent:\n'
                '    event_id: str\n'
                '    aggregate_id: str\n'
                '    event_type: str  # "ACCOUNT_OPENED", "FUNDS_DEPOSITED", "FUNDS_WITHDRAWN"\n'
                '    payload: Dict[str, Any]\n'
                '    version: int\n'
            ),
            "snapshot.py": (
                '"""Aggregate state snapshot."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Any, Dict\n\n\n'
                '@dataclass\n'
                'class AccountSnapshot:\n'
                '    aggregate_id: str\n'
                '    balance: float\n'
                '    status: str\n'
                '    version: int\n'
            ),
            "aggregate.py": (
                '"""Bank account domain aggregate with event rehydration."""\n\n'
                'from typing import List, Optional\n'
                'from events import DomainEvent\n'
                'from snapshot import AccountSnapshot\n\n\n'
                'class BankAccountAggregate:\n'
                '    def __init__(self, account_id: str):\n'
                '        self.account_id = account_id\n'
                '        self.balance: float = 0.0\n'
                '        self.status: str = "UNINITIALIZED"\n'
                '        self.version: int = 0\n'
                '        self.uncommitted_events: List[DomainEvent] = []\n\n'
                '    def apply_event(self, event: DomainEvent) -> None:\n'
                '        if event.event_type == "ACCOUNT_OPENED":\n'
                '            self.status = "OPEN"\n'
                '            self.balance = float(event.payload.get("initial_deposit", 0.0))\n'
                '        elif event.event_type == "FUNDS_DEPOSITED":\n'
                '            self.balance += float(event.payload.get("amount", 0.0))\n'
                '        elif event.event_type == "FUNDS_WITHDRAWN":\n'
                '            self.balance -= float(event.payload.get("amount", 0.0))\n'
                '        self.version = event.version\n\n'
                '    def restore_from_snapshot(self, snap: AccountSnapshot) -> None:\n'
                '        self.balance = snap.balance\n'
                '        self.status = snap.status\n'
                '        self.version = snap.version\n'
            ),
            "event_store.py": (
                '"""Append-only event journal store."""\n\n'
                'from typing import Dict, List, Optional\n'
                'from events import DomainEvent\n'
                'from snapshot import AccountSnapshot\n\n\n'
                'class EventStore:\n'
                '    def __init__(self):\n'
                '        self._events: Dict[str, List[DomainEvent]] = {}\n'
                '        self._snapshots: Dict[str, AccountSnapshot] = {}\n\n'
                '    def append_events(self, aggregate_id: str, events: List[DomainEvent]) -> None:\n'
                '        if aggregate_id not in self._events:\n'
                '            self._events[aggregate_id] = []\n'
                '        self._events[aggregate_id].extend(events)\n\n'
                '    def get_events_after(self, aggregate_id: str, after_version: int) -> List[DomainEvent]:\n'
                '        all_ev = self._events.get(aggregate_id, [])\n'
                '        # BUG: Uses >= instead of > for after_version, re-applying events included in snapshot!\n'
                '        return [e for e in all_ev if e.version >= after_version]\n\n'
                '    def save_snapshot(self, snap: AccountSnapshot) -> None:\n'
                '        self._snapshots[snap.aggregate_id] = snap\n\n'
                '    def get_latest_snapshot(self, aggregate_id: str) -> Optional[AccountSnapshot]:\n'
                '        return self._snapshots.get(aggregate_id)\n'
            ),
            "repository.py": (
                '"""Account aggregate repository managing rehydration from snapshot + journal."""\n\n'
                'from typing import Optional\n'
                'from aggregate import BankAccountAggregate\n'
                'from event_store import EventStore\n\n\n'
                'class AccountRepository:\n'
                '    def __init__(self, store: EventStore):\n'
                '        self.store = store\n\n'
                '    def load(self, account_id: str) -> Optional[BankAccountAggregate]:\n'
                '        snap = self.store.get_latest_snapshot(account_id)\n'
                '        account = BankAccountAggregate(account_id)\n'
                '        base_version = 0\n'
                '        if snap:\n'
                '            account.restore_from_snapshot(snap)\n'
                '            base_version = snap.version\n\n'
                '        events = self.store.get_events_after(account_id, base_version)\n'
                '        if not snap and not events:\n'
                '            return None\n\n'
                '        for ev in events:\n'
                '            account.apply_event(ev)\n'
                '        return account\n'
            ),
        }

        reference_fix = {
            "event_store.py": (
                '"""Append-only event journal store."""\n\n'
                'from typing import Dict, List, Optional\n'
                'from events import DomainEvent\n'
                'from snapshot import AccountSnapshot\n\n\n'
                'class EventStore:\n'
                '    def __init__(self):\n'
                '        self._events: Dict[str, List[DomainEvent]] = {}\n'
                '        self._snapshots: Dict[str, AccountSnapshot] = {}\n\n'
                '    def append_events(self, aggregate_id: str, events: List[DomainEvent]) -> None:\n'
                '        if aggregate_id not in self._events:\n'
                '            self._events[aggregate_id] = []\n'
                '        self._events[aggregate_id].extend(events)\n\n'
                '    def get_events_after(self, aggregate_id: str, after_version: int) -> List[DomainEvent]:\n'
                '        all_ev = self._events.get(aggregate_id, [])\n'
                '        return [e for e in all_ev if e.version > after_version]\n\n'
                '    def save_snapshot(self, snap: AccountSnapshot) -> None:\n'
                '        self._snapshots[snap.aggregate_id] = snap\n\n'
                '    def get_latest_snapshot(self, aggregate_id: str) -> Optional[AccountSnapshot]:\n'
                '        return self._snapshots.get(aggregate_id)\n'
            )
        }

        tests = {
            "test_event_sourcing.py": (
                'from events import DomainEvent\n'
                'from snapshot import AccountSnapshot\n'
                'from event_store import EventStore\n'
                'from repository import AccountRepository\n\n\n'
                'def test_rehydration_from_events_only():\n'
                '    store = EventStore()\n'
                '    repo = AccountRepository(store)\n'
                '    store.append_events("acc_1", [\n'
                '        DomainEvent("e1", "acc_1", "ACCOUNT_OPENED", {"initial_deposit": 500.0}, 1),\n'
                '        DomainEvent("e2", "acc_1", "FUNDS_DEPOSITED", {"amount": 200.0}, 2),\n'
                '        DomainEvent("e3", "acc_1", "FUNDS_WITHDRAWN", {"amount": 150.0}, 3),\n'
                '    ])\n'
                '    acc = repo.load("acc_1")\n'
                '    assert acc is not None\n'
                '    assert acc.balance == 550.0\n'
                '    assert acc.version == 3\n'
                '    assert acc.status == "OPEN"\n\n\n'
                'def test_rehydration_from_snapshot_and_subsequent_events():\n'
                '    store = EventStore()\n'
                '    repo = AccountRepository(store)\n'
                '    # Snapshot at version 2 with balance 700.0\n'
                '    snap = AccountSnapshot("acc_2", 700.0, "OPEN", 2)\n'
                '    store.save_snapshot(snap)\n'
                '    # Event journal contains v1, v2, v3, v4\n'
                '    store.append_events("acc_2", [\n'
                '        DomainEvent("e1", "acc_2", "ACCOUNT_OPENED", {"initial_deposit": 500.0}, 1),\n'
                '        DomainEvent("e2", "acc_2", "FUNDS_DEPOSITED", {"amount": 200.0}, 2),\n'
                '        DomainEvent("e3", "acc_2", "FUNDS_DEPOSITED", {"amount": 50.0}, 3),\n'
                '        DomainEvent("e4", "acc_2", "FUNDS_WITHDRAWN", {"amount": 100.0}, 4),\n'
                '    ])\n'
                '    # Rehydration MUST NOT re-apply event v2 (which was already in snapshot balance of 700.0)!\n'
                '    acc = repo.load("acc_2")\n'
                '    assert acc is not None\n'
                '    # Expected balance: 700 + 50 - 100 = 650.0\n'
                '    assert acc.balance == 650.0\n'
                '    assert acc.version == 4\n\n\n'
                'def test_nonexistent_account_returns_none():\n'
                '    store = EventStore()\n'
                '    repo = AccountRepository(store)\n'
                '    assert repo.load("acc_ghost") is None\n\n\n'
                'def test_snapshot_at_latest_version():\n'
                '    store = EventStore()\n'
                '    repo = AccountRepository(store)\n'
                '    snap = AccountSnapshot("acc_3", 1000.0, "OPEN", 5)\n'
                '    store.save_snapshot(snap)\n'
                '    store.append_events("acc_3", [\n'
                '        DomainEvent(f"e_{i}", "acc_3", "FUNDS_DEPOSITED", {"amount": 100}, i)\n'
                '        for i in range(1, 6)\n'
                '    ])\n'
                '    acc = repo.load("acc_3")\n'
                '    assert acc is not None\n'
                '    assert acc.balance == 1000.0\n'
                '    assert acc.version == 5\n\n\n'
                'def test_multiple_accounts_rehydration_isolated():\n'
                '    store = EventStore()\n'
                '    repo = AccountRepository(store)\n'
                '    store.append_events("user_a", [DomainEvent("a1", "user_a", "ACCOUNT_OPENED", {"initial_deposit": 100}, 1)])\n'
                '    store.append_events("user_b", [DomainEvent("b1", "user_b", "ACCOUNT_OPENED", {"initial_deposit": 200}, 1)])\n'
                '    acc_a = repo.load("user_a")\n'
                '    acc_b = repo.load("user_b")\n'
                '    assert acc_a.balance == 100\n'
                '    assert acc_b.balance == 200\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "event_sourcing_snapshot_rehydration_version_boundary_leak",
            "categories": ["D", "E", "I"],
            "description": "Event store rehydration queries events using >= snapshot_version instead of >, causing duplicate event application on snapshot restore.",
            "spec_notes": "EventStore.get_events_after must filter events strictly by e.version > after_version.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "state-management",
            },
        }

    def _generate_websocket_fsm(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "frames.py": (
                '"""WebSocket frame representation."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Optional\n\n\n'
                '@dataclass\n'
                'class WSFrame:\n'
                '    opcode: str  # "CONNECT", "AUTH", "TEXT", "PING", "PONG", "CLOSE"\n'
                '    payload: str\n'
                '    auth_token: Optional[str] = None\n'
            ),
            "fsm.py": (
                '"""WebSocket connection protocol finite state machine."""\n\n'
                'class WSState:\n'
                '    DISCONNECTED = "DISCONNECTED"\n'
                '    CONNECTING = "CONNECTING"\n'
                '    AUTHENTICATED = "AUTHENTICATED"\n'
                '    CLOSING = "CLOSING"\n'
                '    CLOSED = "CLOSED"\n'
            ),
            "session.py": (
                '"""WebSocket client session tracking protocol state."""\n\n'
                'from frames import WSFrame\n'
                'from fsm import WSState\n\n\n'
                'class WSSession:\n'
                '    def __init__(self, session_id: str):\n'
                '        self.session_id = session_id\n'
                '        self.state: str = WSState.DISCONNECTED\n'
                '        self.messages_received: list[str] = []\n\n'
                '    def handle_frame(self, frame: WSFrame) -> bool:\n'
                '        if frame.opcode == "CONNECT":\n'
                '            if self.state != WSState.DISCONNECTED:\n'
                '                return False\n'
                '            self.state = WSState.CONNECTING\n'
                '            return True\n\n'
                '        elif frame.opcode == "AUTH":\n'
                '            if self.state != WSState.CONNECTING:\n'
                '                return False\n'
                '            if frame.auth_token == "valid_token":\n'
                '                self.state = WSState.AUTHENTICATED\n'
                '                return True\n'
                '            return False\n\n'
                '        elif frame.opcode == "TEXT":\n'
                '            # BUG: Allows TEXT frames in CONNECTING state before authentication succeeds!\n'
                '            if self.state not in (WSState.CONNECTING, WSState.AUTHENTICATED):\n'
                '                return False\n'
                '            self.messages_received.append(frame.payload)\n'
                '            return True\n\n'
                '        elif frame.opcode == "CLOSE":\n'
                '            self.state = WSState.CLOSED\n'
                '            return True\n\n'
                '        return False\n'
            ),
            "connection_pool.py": (
                '"""Managed pool of active WebSocket client sessions."""\n\n'
                'from typing import Dict, Optional\n'
                'from fsm import WSState\n'
                'from session import WSSession\n\n\n'
                'class WSPool:\n'
                '    def __init__(self):\n'
                '        self.sessions: Dict[str, WSSession] = {}\n\n'
                '    def create_session(self, session_id: str) -> WSSession:\n'
                '        sess = WSSession(session_id)\n'
                '        self.sessions[session_id] = sess\n'
                '        return sess\n\n'
                '    def get_authenticated_count(self) -> int:\n'
                '        return sum(1 for s in self.sessions.values() if s.state == WSState.AUTHENTICATED)\n'
            ),
        }

        reference_fix = {
            "session.py": (
                '"""WebSocket client session tracking protocol state."""\n\n'
                'from frames import WSFrame\n'
                'from fsm import WSState\n\n\n'
                'class WSSession:\n'
                '    def __init__(self, session_id: str):\n'
                '        self.session_id = session_id\n'
                '        self.state: str = WSState.DISCONNECTED\n'
                '        self.messages_received: list[str] = []\n\n'
                '    def handle_frame(self, frame: WSFrame) -> bool:\n'
                '        if frame.opcode == "CONNECT":\n'
                '            if self.state != WSState.DISCONNECTED:\n'
                '                return False\n'
                '            self.state = WSState.CONNECTING\n'
                '            return True\n\n'
                '        elif frame.opcode == "AUTH":\n'
                '            if self.state != WSState.CONNECTING:\n'
                '                return False\n'
                '            if frame.auth_token == "valid_token":\n'
                '                self.state = WSState.AUTHENTICATED\n'
                '                return True\n'
                '            return False\n\n'
                '        elif frame.opcode == "TEXT":\n'
                '            # Strictly require AUTHENTICATED state for message ingestion\n'
                '            if self.state != WSState.AUTHENTICATED:\n'
                '                return False\n'
                '            self.messages_received.append(frame.payload)\n'
                '            return True\n\n'
                '        elif frame.opcode == "CLOSE":\n'
                '            self.state = WSState.CLOSED\n'
                '            return True\n\n'
                '        return False\n'
            )
        }

        tests = {
            "test_websocket_fsm.py": (
                'from frames import WSFrame\n'
                'from fsm import WSState\n'
                'from session import WSSession\n'
                'from connection_pool import WSPool\n\n\n'
                'def test_valid_handshake_and_auth_flow():\n'
                '    sess = WSSession("s1")\n'
                '    assert sess.handle_frame(WSFrame("CONNECT", "")) is True\n'
                '    assert sess.state == WSState.CONNECTING\n'
                '    assert sess.handle_frame(WSFrame("AUTH", "", auth_token="valid_token")) is True\n'
                '    assert sess.state == WSState.AUTHENTICATED\n'
                '    assert sess.handle_frame(WSFrame("TEXT", "hello world")) is True\n'
                '    assert sess.messages_received == ["hello world"]\n\n\n'
                'def test_unauthenticated_text_frame_rejected():\n'
                '    sess = WSSession("s2")\n'
                '    sess.handle_frame(WSFrame("CONNECT", ""))\n'
                '    # Attempting to send TEXT frame while in CONNECTING state must be rejected\n'
                '    assert sess.handle_frame(WSFrame("TEXT", "unauthorized message")) is False\n'
                '    assert len(sess.messages_received) == 0\n\n\n'
                'def test_invalid_auth_token_stays_unauthenticated():\n'
                '    sess = WSSession("s3")\n'
                '    sess.handle_frame(WSFrame("CONNECT", ""))\n'
                '    assert sess.handle_frame(WSFrame("AUTH", "", auth_token="bad_token")) is False\n'
                '    assert sess.state == WSState.CONNECTING\n'
                '    assert sess.handle_frame(WSFrame("TEXT", "payload")) is False\n\n\n'
                'def test_close_transition():\n'
                '    sess = WSSession("s4")\n'
                '    sess.handle_frame(WSFrame("CONNECT", ""))\n'
                '    sess.handle_frame(WSFrame("AUTH", "", auth_token="valid_token"))\n'
                '    assert sess.handle_frame(WSFrame("CLOSE", "")) is True\n'
                '    assert sess.state == WSState.CLOSED\n'
                '    assert sess.handle_frame(WSFrame("TEXT", "post-close")) is False\n\n\n'
                'def test_pool_authenticated_count():\n'
                '    pool = WSPool()\n'
                '    s1 = pool.create_session("u1")\n'
                '    s2 = pool.create_session("u2")\n'
                '    s1.handle_frame(WSFrame("CONNECT", ""))\n'
                '    s1.handle_frame(WSFrame("AUTH", "", auth_token="valid_token"))\n'
                '    s2.handle_frame(WSFrame("CONNECT", ""))\n'
                '    assert pool.get_authenticated_count() == 1\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "websocket_fsm_unauthenticated_state_transition_bypass",
            "categories": ["D", "L", "G"],
            "description": "WebSocket session state machine accepts text payload frames during CONNECTING state before authentication verification.",
            "spec_notes": "WSSession.handle_frame must strictly require state == WSState.AUTHENTICATED for TEXT opcode.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "networking",
            },
        }

    def _generate_compensating_nesting(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "action.py": (
                '"""Atomic workflow action unit."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Callable, Optional\n\n\n'
                '@dataclass\n'
                'class ActionUnit:\n'
                '    name: str\n'
                '    execute_fn: Callable[[], bool]\n'
                '    compensate_fn: Callable[[], None]\n'
            ),
            "step.py": (
                '"""Workflow composite execution step."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import List\n'
                'from action import ActionUnit\n\n\n'
                '@dataclass\n'
                'class WorkflowStep:\n'
                '    step_id: str\n'
                '    actions: List[ActionUnit]\n'
            ),
            "context.py": (
                '"""Workflow execution context telemetry."""\n\n'
                'from dataclasses import dataclass, field\n'
                'from typing import List\n\n\n'
                '@dataclass\n'
                'class WorkflowContext:\n'
                '    workflow_id: str\n'
                '    executed_actions: List[str] = field(default_factory=list)\n'
                '    compensated_actions: List[str] = field(default_factory=list)\n'
                '    success: bool = False\n'
            ),
            "compensator.py": (
                '"""Compensating transaction stack orchestrator."""\n\n'
                'from typing import List\n'
                'from action import ActionUnit\n'
                'from context import WorkflowContext\n\n\n'
                'class CompensatorEngine:\n'
                '    def __init__(self):\n'
                '        self._stack: List[ActionUnit] = []\n\n'
                '    def register_executed(self, action: ActionUnit) -> None:\n'
                '        self._stack.append(action)\n\n'
                '    def compensate_all(self, ctx: WorkflowContext) -> None:\n'
                '        # BUG: Compensates in FIFO insertion order instead of LIFO reverse stack order!\n'
                '        while self._stack:\n'
                '            action = self._stack.pop(0)  # BUG: pop(0) instead of pop()\n'
                '            action.compensate_fn()\n'
                '            ctx.compensated_actions.append(action.name)\n'
            ),
            "workflow.py": (
                '"""Nested workflow executor."""\n\n'
                'from typing import List\n'
                'from action import ActionUnit\n'
                'from compensator import CompensatorEngine\n'
                'from context import WorkflowContext\n'
                'from step import WorkflowStep\n\n\n'
                'class NestedWorkflowExecutor:\n'
                '    def __init__(self):\n'
                '        self.compensator = CompensatorEngine()\n\n'
                '    def run_workflow(self, workflow_id: str, steps: List[WorkflowStep]) -> WorkflowContext:\n'
                '        ctx = WorkflowContext(workflow_id=workflow_id)\n'
                '        for step in steps:\n'
                '            for action in step.actions:\n'
                '                ok = action.execute_fn()\n'
                '                if not ok:\n'
                '                    self.compensator.compensate_all(ctx)\n'
                '                    ctx.success = False\n'
                '                    return ctx\n'
                '                self.compensator.register_executed(action)\n'
                '                ctx.executed_actions.append(action.name)\n'
                '        ctx.success = True\n'
                '        return ctx\n'
            ),
        }

        reference_fix = {
            "compensator.py": (
                '"""Compensating transaction stack orchestrator."""\n\n'
                'from typing import List\n'
                'from action import ActionUnit\n'
                'from context import WorkflowContext\n\n\n'
                'class CompensatorEngine:\n'
                '    def __init__(self):\n'
                '        self._stack: List[ActionUnit] = []\n\n'
                '    def register_executed(self, action: ActionUnit) -> None:\n'
                '        self._stack.append(action)\n\n'
                '    def compensate_all(self, ctx: WorkflowContext) -> None:\n'
                '        # LIFO reverse order compensation\n'
                '        while self._stack:\n'
                '            action = self._stack.pop()\n'
                '            action.compensate_fn()\n'
                '            ctx.compensated_actions.append(action.name)\n'
            )
        }

        tests = {
            "test_compensating_workflow.py": (
                'from action import ActionUnit\n'
                'from step import WorkflowStep\n'
                'from workflow import NestedWorkflowExecutor\n\n\n'
                'def test_happy_path_all_steps_succeed():\n'
                '    wf = NestedWorkflowExecutor()\n'
                '    a1 = ActionUnit("reserve_credit", lambda: True, lambda: None)\n'
                '    a2 = ActionUnit("allocate_resource", lambda: True, lambda: None)\n'
                '    step1 = WorkflowStep("step_1", [a1, a2])\n'
                '    ctx = wf.run_workflow("wf_1", [step1])\n'
                '    assert ctx.success is True\n'
                '    assert ctx.executed_actions == ["reserve_credit", "allocate_resource"]\n'
                '    assert len(ctx.compensated_actions) == 0\n\n\n'
                'def test_lifo_reverse_compensation_on_failure():\n'
                '    wf = NestedWorkflowExecutor()\n'
                '    log: list[str] = []\n'
                '    a1 = ActionUnit("step_1", lambda: True, lambda: log.append("rollback_1"))\n'
                '    a2 = ActionUnit("step_2", lambda: True, lambda: log.append("rollback_2"))\n'
                '    a3 = ActionUnit("step_3", lambda: False, lambda: log.append("rollback_3"))  # Fails\n'
                '    step = WorkflowStep("all_steps", [a1, a2, a3])\n'
                '    ctx = wf.run_workflow("wf_fail", [step])\n'
                '    assert ctx.success is False\n'
                '    assert ctx.executed_actions == ["step_1", "step_2"]\n'
                '    # LIFO compensation order: rollback_2 must execute before rollback_1!\n'
                '    assert ctx.compensated_actions == ["step_2", "step_1"]\n'
                '    assert log == ["rollback_2", "rollback_1"]\n\n\n'
                'def test_first_action_failure_no_compensations():\n'
                '    wf = NestedWorkflowExecutor()\n'
                '    a1 = ActionUnit("init", lambda: False, lambda: None)\n'
                '    ctx = wf.run_workflow("wf_empty", [WorkflowStep("s1", [a1])])\n'
                '    assert ctx.success is False\n'
                '    assert len(ctx.executed_actions) == 0\n'
                '    assert len(ctx.compensated_actions) == 0\n\n\n'
                'def test_multi_step_workflow_partial_rollback():\n'
                '    wf = NestedWorkflowExecutor()\n'
                '    calls: list[str] = []\n'
                '    s1_a1 = ActionUnit("db_insert", lambda: True, lambda: calls.append("undo_db"))\n'
                '    s1_a2 = ActionUnit("cache_set", lambda: True, lambda: calls.append("undo_cache"))\n'
                '    s2_a1 = ActionUnit("email_send", lambda: True, lambda: calls.append("undo_email"))\n'
                '    s2_a2 = ActionUnit("payment_charge", lambda: False, lambda: calls.append("undo_pay"))\n'
                '    steps = [WorkflowStep("s1", [s1_a1, s1_a2]), WorkflowStep("s2", [s2_a1, s2_a2])]\n'
                '    ctx = wf.run_workflow("wf_multi", steps)\n'
                '    assert ctx.success is False\n'
                '    assert ctx.compensated_actions == ["email_send", "cache_set", "db_insert"]\n'
                '    assert calls == ["undo_email", "undo_cache", "undo_db"]\n\n\n'
                'def test_empty_steps_list():\n'
                '    wf = NestedWorkflowExecutor()\n'
                '    ctx = wf.run_workflow("wf_zero", [])\n'
                '    assert ctx.success is True\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "compensating_transaction_fifo_rollback_inversion",
            "categories": ["D", "E"],
            "description": "Compensating transaction stack executes compensations in FIFO queue order instead of LIFO reverse order on workflow abort.",
            "spec_notes": "CompensatorEngine.compensate_all must pop actions using LIFO order (self._stack.pop()).",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "e-commerce",
            },
        }

    def _generate_cloud_provisioning_saga(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "models.py": (
                '"""Cloud infrastructure models."""\n\n'
                'from dataclasses import dataclass, field\n'
                'from typing import List, Optional\n\n\n'
                '@dataclass\n'
                'class ProvisioningRequest:\n'
                '    cluster_id: str\n'
                '    cidr_block: str\n'
                '    node_count: int\n'
                '    domain_name: str\n'
                '    status: str = "PENDING"\n'
                '    allocated_resources: List[str] = field(default_factory=list)\n'
                '    released_resources: List[str] = field(default_factory=list)\n'
            ),
            "vpc_service.py": (
                '"""Virtual private cloud network allocator."""\n\n'
                'class VPCService:\n'
                '    def __init__(self):\n'
                '        self.allocated_subnets: set[str] = set()\n\n'
                '    def allocate_subnet(self, cidr: str) -> bool:\n'
                '        if cidr in self.allocated_subnets:\n'
                '            return False\n'
                '        self.allocated_subnets.add(cidr)\n'
                '        return True\n\n'
                '    def release_subnet(self, cidr: str) -> None:\n'
                '        self.allocated_subnets.discard(cidr)\n'
            ),
            "compute_service.py": (
                '"""Compute cluster provisioning service."""\n\n'
                'from typing import Dict\n\n\n'
                'class ComputeService:\n'
                '    def __init__(self, max_capacity: int = 100):\n'
                '        self.max_capacity = max_capacity\n'
                '        self.active_nodes: Dict[str, int] = {}\n\n'
                '    def provision_nodes(self, cluster_id: str, count: int) -> bool:\n'
                '        current_used = sum(self.active_nodes.values())\n'
                '        if current_used + count > self.max_capacity:\n'
                '            return False\n'
                '        self.active_nodes[cluster_id] = count\n'
                '        return True\n\n'
                '    def terminate_nodes(self, cluster_id: str) -> None:\n'
                '        self.active_nodes.pop(cluster_id, None)\n'
            ),
            "dns_service.py": (
                '"""DNS record mapping service."""\n\n'
                'from typing import Dict\n\n\n'
                'class DNSService:\n'
                '    def __init__(self):\n'
                '        self.records: Dict[str, str] = {}\n\n'
                '    def bind_record(self, domain: str, target: str) -> bool:\n'
                '        if not domain or domain.endswith(".invalid"):\n'
                '            return False\n'
                '        self.records[domain] = target\n'
                '        return True\n\n'
                '    def unbind_record(self, domain: str) -> None:\n'
                '        self.records.pop(domain, None)\n'
            ),
            "orchestrator.py": (
                '"""Distributed cloud provisioning saga orchestrator."""\n\n'
                'from compute_service import ComputeService\n'
                'from dns_service import DNSService\n'
                'from models import ProvisioningRequest\n'
                'from vpc_service import VPCService\n\n\n'
                'class CloudProvisioningSaga:\n'
                '    def __init__(self, vpc: VPCService, compute: ComputeService, dns: DNSService):\n'
                '        self.vpc = vpc\n'
                '        self.compute = compute\n'
                '        self.dns = dns\n\n'
                '    def provision_cluster(self, req: ProvisioningRequest) -> bool:\n'
                '        # Step 1: Allocate VPC Subnet\n'
                '        if not self.vpc.allocate_subnet(req.cidr_block):\n'
                '            req.status = "FAILED_VPC"\n'
                '            return False\n'
                '        req.allocated_resources.append("VPC")\n\n'
                '        # Step 2: Provision Compute Nodes\n'
                '        if not self.compute.provision_nodes(req.cluster_id, req.node_count):\n'
                '            # Compensate VPC\n'
                '            self.vpc.release_subnet(req.cidr_block)\n'
                '            req.released_resources.append("VPC")\n'
                '            req.status = "FAILED_COMPUTE"\n'
                '            return False\n'
                '        req.allocated_resources.append("COMPUTE")\n\n'
                '        # Step 3: Bind DNS Domain\n'
                '        if not self.dns.bind_record(req.domain_name, req.cluster_id):\n'
                '            # Compensate Compute\n'
                '            self.compute.terminate_nodes(req.cluster_id)\n'
                '            req.released_resources.append("COMPUTE")\n'
                '            # BUG: Misses compensating VPC subnet allocation on DNS failure, leaking CIDR leases!\n'
                '            req.status = "FAILED_DNS"\n'
                '            return False\n'
                '        req.allocated_resources.append("DNS")\n'
                '        req.status = "PROVISIONED"\n'
                '        return True\n'
            ),
        }

        reference_fix = {
            "orchestrator.py": (
                '"""Distributed cloud provisioning saga orchestrator."""\n\n'
                'from compute_service import ComputeService\n'
                'from dns_service import DNSService\n'
                'from models import ProvisioningRequest\n'
                'from vpc_service import VPCService\n\n\n'
                'class CloudProvisioningSaga:\n'
                '    def __init__(self, vpc: VPCService, compute: ComputeService, dns: DNSService):\n'
                '        self.vpc = vpc\n'
                '        self.compute = compute\n'
                '        self.dns = dns\n\n'
                '    def provision_cluster(self, req: ProvisioningRequest) -> bool:\n'
                '        if not self.vpc.allocate_subnet(req.cidr_block):\n'
                '            req.status = "FAILED_VPC"\n'
                '            return False\n'
                '        req.allocated_resources.append("VPC")\n\n'
                '        if not self.compute.provision_nodes(req.cluster_id, req.node_count):\n'
                '            self.vpc.release_subnet(req.cidr_block)\n'
                '            req.released_resources.append("VPC")\n'
                '            req.status = "FAILED_COMPUTE"\n'
                '            return False\n'
                '        req.allocated_resources.append("COMPUTE")\n\n'
                '        if not self.dns.bind_record(req.domain_name, req.cluster_id):\n'
                '            self.compute.terminate_nodes(req.cluster_id)\n'
                '            req.released_resources.append("COMPUTE")\n'
                '            self.vpc.release_subnet(req.cidr_block)\n'
                '            req.released_resources.append("VPC")\n'
                '            req.status = "FAILED_DNS"\n'
                '            return False\n'
                '        req.allocated_resources.append("DNS")\n'
                '        req.status = "PROVISIONED"\n'
                '        return True\n'
            )
        }

        tests = {
            "test_cloud_saga.py": (
                'from models import ProvisioningRequest\n'
                'from vpc_service import VPCService\n'
                'from compute_service import ComputeService\n'
                'from dns_service import DNSService\n'
                'from orchestrator import CloudProvisioningSaga\n\n\n'
                'def test_successful_provisioning_all_steps():\n'
                '    vpc = VPCService()\n'
                '    compute = ComputeService()\n'
                '    dns = DNSService()\n'
                '    saga = CloudProvisioningSaga(vpc, compute, dns)\n'
                '    req = ProvisioningRequest("c1", "10.0.0.0/24", 5, "cluster1.cloud.net")\n'
                '    assert saga.provision_cluster(req) is True\n'
                '    assert req.status == "PROVISIONED"\n'
                '    assert "10.0.0.0/24" in vpc.allocated_subnets\n'
                '    assert compute.active_nodes["c1"] == 5\n'
                '    assert dns.records["cluster1.cloud.net"] == "c1"\n\n\n'
                'def test_dns_failure_compensates_both_compute_and_vpc():\n'
                '    vpc = VPCService()\n'
                '    compute = ComputeService()\n'
                '    dns = DNSService()\n'
                '    saga = CloudProvisioningSaga(vpc, compute, dns)\n'
                '    # .invalid TLD fails in DNSService\n'
                '    req = ProvisioningRequest("c2", "10.0.1.0/24", 10, "broken.invalid")\n'
                '    assert saga.provision_cluster(req) is False\n'
                '    assert req.status == "FAILED_DNS"\n'
                '    # CRITICAL: Both compute AND VPC must be fully released\n'
                '    assert "10.0.1.0/24" not in vpc.allocated_subnets\n'
                '    assert "c2" not in compute.active_nodes\n'
                '    assert req.released_resources == ["COMPUTE", "VPC"]\n\n\n'
                'def test_compute_overcapacity_compensates_vpc():\n'
                '    vpc = VPCService()\n'
                '    compute = ComputeService(max_capacity=5)\n'
                '    dns = DNSService()\n'
                '    saga = CloudProvisioningSaga(vpc, compute, dns)\n'
                '    req = ProvisioningRequest("c3", "10.0.2.0/24", 10, "large.cloud.net")\n'
                '    assert saga.provision_cluster(req) is False\n'
                '    assert req.status == "FAILED_COMPUTE"\n'
                '    assert "10.0.2.0/24" not in vpc.allocated_subnets\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "distributed_cloud_provisioning_saga_partial_compensation_leak",
            "categories": ["E", "I", "D"],
            "description": "Distributed cloud saga orchestrator fails to compensate VPC network allocation upon DNS step failure, leaking CIDR leases.",
            "spec_notes": "CloudProvisioningSaga.provision_cluster must release VPC allocation in reverse order when DNS binding fails.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "cloud-infrastructure",
            },
        }

    def _generate_two_phase_commit(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "tx_state.py": (
                '"""2PC transaction status states."""\n\n'
                'class TxState:\n'
                '    INIT = "INIT"\n'
                '    PREPARED = "PREPARED"\n'
                '    COMMITTED = "COMMITTED"\n'
                '    ABORTED = "ABORTED"\n'
            ),
            "coordinator_log.py": (
                '"""Coordinator write-ahead transaction log."""\n\n'
                'from dataclasses import dataclass\n'
                'from typing import Dict, List\n\n\n'
                '@dataclass\n'
                'class LogRecord:\n'
                '    tx_id: str\n'
                '    state: str\n'
                '    participants: List[str]\n\n\n'
                'class CoordinatorWAL:\n'
                '    def __init__(self):\n'
                '        self.records: Dict[str, LogRecord] = {}\n\n'
                '    def write(self, tx_id: str, state: str, participants: List[str]) -> None:\n'
                '        self.records[tx_id] = LogRecord(tx_id, state, list(participants))\n'
            ),
            "participant.py": (
                '"""2PC participant resource manager."""\n\n'
                'from typing import Dict\n'
                'from tx_state import TxState\n\n\n'
                'class ParticipantRM:\n'
                '    def __init__(self, rm_id: str):\n'
                '        self.rm_id = rm_id\n'
                '        self.prepared_txs: set[str] = set()\n'
                '        self.committed_txs: set[str] = set()\n'
                '        self.aborted_txs: set[str] = set()\n\n'
                '    def prepare(self, tx_id: str) -> bool:\n'
                '        self.prepared_txs.add(tx_id)\n'
                '        return True\n\n'
                '    def commit(self, tx_id: str) -> None:\n'
                '        self.prepared_txs.discard(tx_id)\n'
                '        self.committed_txs.add(tx_id)\n\n'
                '    def abort(self, tx_id: str) -> None:\n'
                '        self.prepared_txs.discard(tx_id)\n'
                '        self.aborted_txs.add(tx_id)\n'
            ),
            "recovery_engine.py": (
                '"""Coordinator crash recovery engine."""\n\n'
                'from typing import Dict, List\n'
                'from coordinator_log import CoordinatorWAL\n'
                'from participant import ParticipantRM\n'
                'from tx_state import TxState\n\n\n'
                'class TwoPhaseRecoveryEngine:\n'
                '    def __init__(self, wal: CoordinatorWAL, participants: Dict[str, ParticipantRM]):\n'
                '        self.wal = wal\n'
                '        self.participants = participants\n\n'
                '    def recover_all_transactions(self) -> Dict[str, str]:\n'
                '        results: Dict[str, str] = {}\n'
                '        for tx_id, record in self.wal.records.items():\n'
                '            if record.state == TxState.COMMITTED:\n'
                '                # Ensure all participants committed\n'
                '                for p_id in record.participants:\n'
                '                    self.participants[p_id].commit(tx_id)\n'
                '                results[tx_id] = TxState.COMMITTED\n'
                '            elif record.state == TxState.PREPARED:\n'
                '                # BUG: When coordinator crashed after writing PREPARED (all voted YES),\n'
                '                # it aborts the transaction instead of completing the commit!\n'
                '                for p_id in record.participants:\n'
                '                    self.participants[p_id].abort(tx_id)\n'
                '                results[tx_id] = TxState.ABORTED\n'
                '            elif record.state in (TxState.INIT, TxState.ABORTED):\n'
                '                for p_id in record.participants:\n'
                '                    self.participants[p_id].abort(tx_id)\n'
                '                results[tx_id] = TxState.ABORTED\n'
                '        return results\n'
            ),
        }

        reference_fix = {
            "recovery_engine.py": (
                '"""Coordinator crash recovery engine."""\n\n'
                'from typing import Dict, List\n'
                'from coordinator_log import CoordinatorWAL\n'
                'from participant import ParticipantRM\n'
                'from tx_state import TxState\n\n\n'
                'class TwoPhaseRecoveryEngine:\n'
                '    def __init__(self, wal: CoordinatorWAL, participants: Dict[str, ParticipantRM]):\n'
                '        self.wal = wal\n'
                '        self.participants = participants\n\n'
                '    def recover_all_transactions(self) -> Dict[str, str]:\n'
                '        results: Dict[str, str] = {}\n'
                '        for tx_id, record in self.wal.records.items():\n'
                '            if record.state in (TxState.COMMITTED, TxState.PREPARED):\n'
                '                # If PREPARED was logged, all participants voted YES before crash; commit forward\n'
                '                for p_id in record.participants:\n'
                '                    self.participants[p_id].commit(tx_id)\n'
                '                self.wal.write(tx_id, TxState.COMMITTED, record.participants)\n'
                '                results[tx_id] = TxState.COMMITTED\n'
                '            elif record.state in (TxState.INIT, TxState.ABORTED):\n'
                '                for p_id in record.participants:\n'
                '                    self.participants[p_id].abort(tx_id)\n'
                '                results[tx_id] = TxState.ABORTED\n'
                '        return results\n'
            )
        }

        tests = {
            "test_2pc_recovery.py": (
                'from coordinator_log import CoordinatorWAL\n'
                'from participant import ParticipantRM\n'
                'from recovery_engine import TwoPhaseRecoveryEngine\n'
                'from tx_state import TxState\n\n\n'
                'def test_prepared_transaction_commits_forward_on_recovery():\n'
                '    wal = CoordinatorWAL()\n'
                '    p1 = ParticipantRM("rm_1")\n'
                '    p2 = ParticipantRM("rm_2")\n'
                '    p1.prepare("tx_100")\n'
                '    p2.prepare("tx_100")\n'
                '    # Coordinator logged PREPARED then crashed\n'
                '    wal.write("tx_100", TxState.PREPARED, ["rm_1", "rm_2"])\n'
                '    engine = TwoPhaseRecoveryEngine(wal, {"rm_1": p1, "rm_2": p2})\n'
                '    res = engine.recover_all_transactions()\n'
                '    assert res["tx_100"] == TxState.COMMITTED\n'
                '    assert "tx_100" in p1.committed_txs\n'
                '    assert "tx_100" in p2.committed_txs\n\n\n'
                'def test_init_transaction_aborts_on_recovery():\n'
                '    wal = CoordinatorWAL()\n'
                '    p1 = ParticipantRM("rm_1")\n'
                '    wal.write("tx_init", TxState.INIT, ["rm_1"])\n'
                '    engine = TwoPhaseRecoveryEngine(wal, {"rm_1": p1})\n'
                '    res = engine.recover_all_transactions()\n'
                '    assert res["tx_init"] == TxState.ABORTED\n'
                '    assert "tx_init" in p1.aborted_txs\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "two_phase_commit_prepared_recovery_abort_error",
            "categories": ["E", "I", "G"],
            "description": "2PC coordinator crash recovery aborts transactions in PREPARED state instead of committing forward, violating atomic commit.",
            "spec_notes": "TwoPhaseRecoveryEngine must commit forward when recovering logged PREPARED transactions.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 4,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "distributed-transactions",
            },
        }

    def _generate_crdt_convergence(self, task_id: str, spec: Dict[str, Any], seed: int) -> Dict[str, Any]:
        repo_files = {
            "lww_element_set.py": (
                '"""Last-Write-Wins Element Set (LWW-Element-Set) CRDT."""\n\n'
                'from dataclasses import dataclass, field\n'
                'from typing import Any, Dict, Set\n\n\n'
                'class LWWElementSet:\n'
                '    def __init__(self):\n'
                '        self.add_set: Dict[str, float] = {}     # element -> timestamp\n'
                '        self.remove_set: Dict[str, float] = {}  # element -> timestamp\n\n'
                '    def add(self, element: str, timestamp: float) -> None:\n'
                '        curr = self.add_set.get(element, 0.0)\n'
                '        if timestamp > curr:\n'
                '            self.add_set[element] = timestamp\n\n'
                '    def remove(self, element: str, timestamp: float) -> None:\n'
                '        curr = self.remove_set.get(element, 0.0)\n'
                '        if timestamp > curr:\n'
                '            self.remove_set[element] = timestamp\n\n'
                '    def lookup(self, element: str) -> bool:\n'
                '        add_ts = self.add_set.get(element)\n'
                '        if add_ts is None:\n'
                '            return False\n'
                '        rem_ts = self.remove_set.get(element)\n'
                '        if rem_ts is None:\n'
                '            return True\n'
                '        # LWW-Add-Bias Specification: When add_ts == rem_ts, addition wins (add_ts >= rem_ts)\n'
                '        # BUG: Uses strict > which favors removal on timestamp ties!\n'
                '        return add_ts > rem_ts\n\n'
                '    def merge(self, other: "LWWElementSet") -> None:\n'
                '        for el, ts in other.add_set.items():\n'
                '            self.add(el, ts)\n'
                '        for el, ts in other.remove_set.items():\n'
                '            self.remove(el, ts)\n'
            ),
            "replica.py": (
                '"""Distributed node replica storing CRDT sets."""\n\n'
                'from lww_element_set import LWWElementSet\n\n\n'
                'class ReplicaNode:\n'
                '    def __init__(self, node_id: str):\n'
                '        self.node_id = node_id\n'
                '        self.set_crdt = LWWElementSet()\n\n'
                '    def sync_with(self, peer: "ReplicaNode") -> None:\n'
                '        self.set_crdt.merge(peer.set_crdt)\n'
            ),
        }

        reference_fix = {
            "lww_element_set.py": (
                '"""Last-Write-Wins Element Set (LWW-Element-Set) CRDT."""\n\n'
                'from typing import Any, Dict, Set\n\n\n'
                'class LWWElementSet:\n'
                '    def __init__(self):\n'
                '        self.add_set: Dict[str, float] = {}\n'
                '        self.remove_set: Dict[str, float] = {}\n\n'
                '    def add(self, element: str, timestamp: float) -> None:\n'
                '        curr = self.add_set.get(element, 0.0)\n'
                '        if timestamp > curr:\n'
                '            self.add_set[element] = timestamp\n\n'
                '    def remove(self, element: str, timestamp: float) -> None:\n'
                '        curr = self.remove_set.get(element, 0.0)\n'
                '        if timestamp > curr:\n'
                '            self.remove_set[element] = timestamp\n\n'
                '    def lookup(self, element: str) -> bool:\n'
                '        add_ts = self.add_set.get(element)\n'
                '        if add_ts is None:\n'
                '            return False\n'
                '        rem_ts = self.remove_set.get(element)\n'
                '        if rem_ts is None:\n'
                '            return True\n'
                '        # LWW-Add-Bias: addition wins on equal timestamps\n'
                '        return add_ts >= rem_ts\n\n'
                '    def merge(self, other: "LWWElementSet") -> None:\n'
                '        for el, ts in other.add_set.items():\n'
                '            self.add(el, ts)\n'
                '        for el, ts in other.remove_set.items():\n'
                '            self.remove(el, ts)\n'
            )
        }

        tests = {
            "test_crdt_convergence.py": (
                'from replica import ReplicaNode\n'
                'from lww_element_set import LWWElementSet\n\n\n'
                'def test_equal_timestamp_add_bias():\n'
                '    s = LWWElementSet()\n'
                '    t = 100.0\n'
                '    s.add("item_1", t)\n'
                '    s.remove("item_1", t)\n'
                '    # Add bias must return True on identical add and remove timestamps\n'
                '    assert s.lookup("item_1") is True\n\n\n'
                'def test_replica_convergence():\n'
                '    r1 = ReplicaNode("r1")\n'
                '    r2 = ReplicaNode("r2")\n'
                '    r1.set_crdt.add("x", 50.0)\n'
                '    r2.set_crdt.remove("x", 40.0)\n'
                '    # Synchronize\n'
                '    r1.sync_with(r2)\n'
                '    r2.sync_with(r1)\n'
                '    assert r1.set_crdt.lookup("x") is True\n'
                '    assert r2.set_crdt.lookup("x") is True\n'
            )
        }

        return {
            "task_id": task_id,
            "suite": "v2",
            "version": 2,
            "difficulty": "hard",
            "bug_type": "crdt_lww_add_bias_tiebreaker_inversion",
            "categories": ["E", "G"],
            "description": "LWW-Element-Set CRDT implements strict > instead of >=, violating specified add-bias resolution on timestamp ties.",
            "spec_notes": "LWWElementSet.lookup must evaluate add_ts >= rem_ts for add-bias tie breaking.",
            "repo_files": repo_files,
            "tests": tests,
            "reference_fix": reference_fix,
            "metadata": {
                "estimated_reasoning_steps": 3,
                "file_count": len(repo_files),
                "adversarial": False,
                "stateful": True,
                "multi_file": True,
                "domain": "distributed-systems",
            },
        }



