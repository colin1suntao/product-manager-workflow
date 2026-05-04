"""原型生成模块"""

from pm_workstation.prototype.component_matcher import ComponentMatcher
from pm_workstation.prototype.html_generator import HTMLGenerator
from pm_workstation.prototype.interaction_configurator import InteractionConfigurator
from pm_workstation.prototype.page_structure import PageNode, PageStructure, PageStructureGenerator
from pm_workstation.prototype.style_checker import StyleConsistencyChecker, StyleConsistencyResult

__all__ = [
    "ComponentMatcher",
    "HTMLGenerator",
    "InteractionConfigurator",
    "PageNode",
    "PageStructure",
    "PageStructureGenerator",
    "StyleConsistencyChecker",
    "StyleConsistencyResult",
]
