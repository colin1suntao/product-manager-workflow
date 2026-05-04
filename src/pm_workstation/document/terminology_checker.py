"""术语一致性检查器

检查文档中的术语使用是否一致。
"""

import re
from collections import defaultdict
from typing import Optional

from pydantic import BaseModel, Field


class TerminologyIssue(BaseModel):
    """术语问题"""
    term: str = Field(..., description="术语")
    variants: list[str] = Field(..., description="变体形式")
    location: str = Field(default="", description="出现位置")
    suggestion: str = Field(default="", description="建议统一使用的形式")


class TerminologyConsistencyResult(BaseModel):
    """术语一致性检查结果"""
    passed: bool = Field(..., description="是否通过")
    issues: list[TerminologyIssue] = Field(default_factory=list, description="问题列表")
    terms_checked: int = Field(default=0, description="检查的术语数量")


class TerminologyConsistencyChecker:
    """术语一致性检查器
    
    检查文档中关键术语的使用是否一致，
    检测同义词、缩写、大小写变体等问题。
    """
    
    def __init__(self, glossary: Optional[dict[str, str]] = None):
        self._glossary = glossary or self._get_default_glossary()
    
    def check(self, document_content: str) -> TerminologyConsistencyResult:
        """检查文档术语一致性
        
        Args:
            document_content: 文档内容
            
        Returns:
            检查结果
        """
        issues = []
        terms_checked = 0
        
        # 检查术语变体
        variant_issues = self._check_term_variants(document_content)
        issues.extend(variant_issues)
        terms_checked += len(self._glossary)
        
        # 检查大小写一致性
        case_issues = self._check_case_consistency(document_content)
        issues.extend(case_issues)
        
        # 检查缩写一致性
        abbr_issues = self._check_abbreviation_consistency(document_content)
        issues.extend(abbr_issues)
        
        return TerminologyConsistencyResult(
            passed=len(issues) == 0,
            issues=issues,
            terms_checked=terms_checked,
        )
    
    def _check_term_variants(self, content: str) -> list[TerminologyIssue]:
        """检查术语变体"""
        issues = []
        
        for canonical, variants in self._glossary.items():
            variant_list = [v.strip() for v in variants.split(",")]
            
            found_variants = []
            for variant in variant_list:
                if re.search(re.escape(variant), content, re.IGNORECASE):
                    found_variants.append(variant)
            
            # 检查是否同时出现了多个变体
            if len(found_variants) > 1:
                issues.append(TerminologyIssue(
                    term=canonical,
                    variants=found_variants,
                    suggestion=f"建议统一使用: {canonical}",
                ))
        
        return issues
    
    def _check_case_consistency(self, content: str) -> list[TerminologyIssue]:
        """检查大小写一致性"""
        issues = []
        
        # 常见的大小写敏感术语
        case_sensitive_terms = ["API", "URL", "ID", "UI", "UX", "HTTP", "JSON", "SQL", "CSS", "HTML"]
        
        for term in case_sensitive_terms:
            # 查找错误的变体
            wrong_forms = {
                "API": ["Api", "api"],
                "URL": ["Url", "url"],
                "ID": ["Id", "id"],
                "UI": ["Ui", "ui"],
                "HTTP": ["Http", "http"],
                "JSON": ["Json", "json"],
            }
            
            wrong_variants = wrong_forms.get(term, [])
            found = []
            
            for wrong in wrong_variants:
                if wrong in content:
                    found.append(wrong)
            
            if found:
                issues.append(TerminologyIssue(
                    term=term,
                    variants=found,
                    suggestion=f"建议统一使用大写形式: {term}",
                ))
        
        return issues
    
    def _check_abbreviation_consistency(self, content: str) -> list[TerminologyIssue]:
        """检查缩写一致性"""
        issues = []
        
        # 常见缩写映射
        abbr_map = {
            "product requirement document": ["PRD"],
            "user interface": ["UI"],
            "user experience": ["UX"],
            "application programming interface": ["API"],
            "representational state transfer": ["REST"],
            "representational state transfer API": ["REST API"],
        }
        
        for full_term, abbreviations in abbr_map.items():
            has_full = bool(re.search(re.escape(full_term), content, re.IGNORECASE))
            has_abbr = any(abbr in content for abbr in abbreviations)
            
            # 如果同时出现全称和缩写，建议统一
            if has_full and has_abbr:
                issues.append(TerminologyIssue(
                    term=full_term,
                    variants=[full_term] + abbreviations,
                    suggestion="建议在首次出现时使用全称+缩写格式，后续统一使用缩写",
                ))
        
        return issues
    
    def add_glossary_entry(self, canonical: str, variants: str):
        """添加术语表条目
        
        Args:
            canonical: 标准术语
            variants: 变体形式（逗号分隔）
        """
        self._glossary[canonical] = variants
    
    def _get_default_glossary(self) -> dict[str, str]:
        """获取默认术语表"""
        return {
            "用户": "使用者,操作员,账号",
            "管理员": "Admin,系统管理员,超级管理员",
            "订单": "Order,定单",
            "商品": "Product,产品,货物",
            "库存": "Stock,库存量",
            "购物车": "Cart,Shopping Cart,购物车",
            "支付": "Payment,付款,缴费",
            "登录": "Login,Sign In,登入",
            "注册": "Register,Sign Up,注册账号",
            "工作台": "Workbench,Dashboard,控制台",
            "原型": "Prototype,样机,Demo",
            "需求": "Requirement,需求说明,需求文档",
        }
