from ast import Str
from pathlib import Path
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QFormLayout,
    QLineEdit,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QCheckBox,
    QDialog,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
)
from PySide6.QtGui import QIntValidator, QDoubleValidator
from PySide6.QtWidgets import QFileDialog
from PySide6.QtCore import Qt

from orgasm import get_command_specs, execute_command


FieldSpec = Tuple[str, Type, List[str]]  # (label, kind, options) where kind in {"text", "dropdown"}


def get_result_widget(result: Any) -> QWidget:
    parent = QWidget()
    layout = QVBoxLayout(parent)
    if isinstance(result, str) or isinstance(result, int) or isinstance(result, float):
        label = QLabel(str(result))
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(label)
    elif isinstance(result, dict):
        # create a scrollable table
        table = QTableWidget(len(result.keys()), 2)
        table.setHorizontalHeaderLabels(["Key", "Value"])
        for row_idx, (key, value) in enumerate(result.items()):
            key_item = QTableWidgetItem(str(key))
            value_item = QTableWidgetItem(str(value))
            table.setItem(row_idx, 0, key_item)
            table.setItem(row_idx, 1, value_item)
        # enable copy functionality
        table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        table.resizeRowsToContents()
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # make it read-only
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        layout.addWidget(table)    
    elif isinstance(result, list):
        if len(result) == 0:
            label = QLabel("No results returned.")
            layout.addWidget(label)
        else:
            if isinstance(result[0], dict):
                # create a scrollable table
                table = QTableWidget(len(result), len(result[0]))
                table.setHorizontalHeaderLabels(result[0].keys())
                for row_idx, row in enumerate(result):
                    for col_idx, (key, value) in enumerate(row.items()):
                        item = QTableWidgetItem(str(value))
                        table.setItem(row_idx, col_idx, item)
                layout.addWidget(table)
            else:
                list_widget = QListWidget()
                for item in result:
                    list_widget.addItem(str(item))
                layout.addWidget(list_widget)
    elif isinstance(result, QWidget):
        # if result is already a QWidget, just return it
        return result
    elif isinstance(result, Path):
        # if result is a Path, display it as a label
        label = QLabel(str(result))
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(label)
    else:
        raise ValueError(f"Unsupported result type: {type(result)}")
    return parent

class ActionWidget(QWidget):
    """Generic widget composed of input fields and an execute button."""

    def __init__(
        self,
        action_name: str,
        fields: List[FieldSpec],
        execute_callback: Callable[[str, Dict[str, str]], str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._action_name = action_name
        self._execute_callback = execute_callback
        self._fields = fields
        self._inputs: Dict[str, Tuple[QWidget, Type]] = {}

        layout = QVBoxLayout(self)
        if fields:
            form = QFormLayout()

            # build inputs according to field spec
            for label, kind, options in fields: 
                if options:
                    w = QComboBox()
                    w.addItems([str(o) for o in options])
                elif kind == str:
                    w = QLineEdit()
                elif kind == bool:
                    w = QCheckBox(label)
                elif kind == Path:
                    txt = QLineEdit()
                    # add a button to open file dialog
                    def open_file_dialog():
                        # path can be file or directory
                        file_path, _ = QFileDialog.getOpenFileName(
                            self, "Select File", str(Path.home()), "All Files (*)")
                        if file_path:
                            txt.setText(file_path)
                    button = QPushButton("Browse")
                    button.clicked.connect(open_file_dialog)
                    w = QWidget()
                    w_layout = QHBoxLayout(w)
                    w_layout.addWidget(txt)
                    w_layout.addWidget(button)
                    w.setLayout(w_layout)
                elif kind == int:
                    w = QLineEdit()
                    w.setValidator(QIntValidator())
                elif kind == float:
                    w = QLineEdit()
                    w.setValidator(QDoubleValidator())
                else:
                    raise ValueError(f"Unknown widget type: {kind}")
                self._inputs[label] = (w, kind)
                form.addRow(label + ":", w)

            layout.addLayout(form)

            # add result display area
            self.result_widget = QWidget(self)
            self.result_widget.setLayout(QVBoxLayout())
            layout.addWidget(self.result_widget)

            # execute button
            exec_btn = QPushButton("Execute")
            exec_btn.clicked.connect(self._on_execute_clicked)
            layout.addWidget(exec_btn, alignment=Qt.AlignmentFlag.AlignRight)
        else:
            result = self._execute_callback(self._action_name, {})
            result_widget = get_result_widget(result)
            if isinstance(result_widget, QWidget):
                layout.addWidget(result_widget)
            else:
                raise ValueError("Result widget must be a QWidget instance.")
            
    # ---------------------------------------------------------------------
    def _collect_values(self) -> Dict[str, str]:
        values: Dict[str, Any] = {}
        for label, (widget, kind) in self._inputs.items():
            if isinstance(widget, QComboBox):
                values[label] = kind(widget.currentText())
            elif isinstance(widget, QLineEdit):
                values[label] = kind(widget.text())
            elif isinstance(widget, QCheckBox):
                values[label] = widget.isChecked()
            elif isinstance(widget, QWidget) and isinstance(widget.layout(), QHBoxLayout) and widget.layout().count() == 2 and isinstance(widget.layout().itemAt(0).widget(), QLineEdit):
                # handle file dialog input
                line_edit = widget.layout().itemAt(0).widget()
                values[label] = kind(line_edit.text()) if line_edit.text() else None
            else:
                raise ValueError(f"Unsupported widget type: {type(widget)}")
        return values

    def _on_execute_clicked(self) -> None:
        values = self._collect_values()
        try:
            result = self._execute_callback(self._action_name, values)
            result_widget = get_result_widget(result)
            if isinstance(result_widget, QWidget):
                # clear previous result
                for i in reversed(range(self.result_widget.layout().count())):
                    item = self.result_widget.layout().itemAt(i)
                    if item.widget():
                        item.widget().deleteLater()
                self.result_widget.layout().addWidget(result_widget)
            else:
                raise ValueError("Result widget must be a QWidget instance.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc), QMessageBox.StandardButton.Ok)

def get_widget_type(arg) -> Type:
    """Return the widget type as a string based on the kind."""
    return arg["type"]

class MainWindow(QMainWindow):
    def __init__(self, classes, title) -> None:
        super().__init__()
        self.setWindowTitle(title)
        self.spec = get_command_specs(classes)
        self.classes = classes
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)

        # sidebar list
        self._sidebar = QListWidget()
        self._sidebar.setFixedWidth(150)
        self._sidebar.currentRowChanged.connect(self._on_sidebar_changed)
        root_layout.addWidget(self._sidebar)

        # stacked pages
        self._stack = QStackedWidget()
        root_layout.addWidget(self._stack, 1)

        # register actions (label, field specs)
        actions: Dict[str, List[FieldSpec]] = {
            cmd["name"]: [
                (arg["name"], get_widget_type(arg), arg.get("valid_values", []) or []) for arg in cmd.get("args", [])
            ] for cmd in self.spec
        }

        for action_name, fields in actions.items():
            self._sidebar.addItem(action_name)
            page = ActionWidget(action_name, fields, self._execute_action)
            self._stack.addWidget(page)

        # select first item by default
        self._sidebar.setCurrentRow(0)

    # ------------------------------------------------------------------
    def _on_sidebar_changed(self, index: int) -> None:
        self._stack.setCurrentIndex(index)

    # ------------------------------------------------------------------
    def _execute_action(self, action_name: str, values: Dict[str, str]) -> str:
        """Dispatch execution based on action name. Returns string result."""
        cmd = next((cmd for cmd in self.spec if cmd["name"] == action_name), None)
        match cmd:
            case None:
                raise ValueError(f"Unknown action: {action_name}")
            case _:
                return execute_command(self.classes, cmd["name"], values)



def create_main_window(classes, title="ORGASM GUI") -> Tuple[QApplication, MainWindow, int]:
    app = QApplication(sys.argv)
    main_window = MainWindow(classes, title)
    main_window.resize(640, 400)
    main_window.show()
    return app, main_window, app.exec()


