class_name ScreenBase
extends Control
## Base for full-screen overlays: dimmed background, safe-area margin, centered content, close signal.

signal done()

var margin: MarginContainer
var center: CenterContainer


func setup(dim_alpha: float = 0.75) -> void:
	theme = UiKit.theme()
	UiKit.full_rect(self)
	mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(UiKit.dim(dim_alpha))
	margin = MarginContainer.new()
	UiKit.full_rect(margin)
	add_child(margin)
	UiKit.apply_safe(margin)
	center = CenterContainer.new()
	margin.add_child(center)


func close() -> void:
	done.emit()
	queue_free()


func _unhandled_input(e: InputEvent) -> void:
	if e.is_action_pressed("cancel"):
		get_viewport().set_input_as_handled()
		close()
