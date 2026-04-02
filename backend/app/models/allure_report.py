"""
Allure Report Statistics Database Models
用于存储 Allure 测试报告的统计数据，支持质量分析和趋势追踪
"""
from sqlalchemy import Column, String, Integer, DateTime, JSON, Enum as SQLEnum, Boolean, ForeignKey, Text, BigInteger, Float
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class TestStatusEnum(str, enum.Enum):
    """Allure test status enum"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BROKEN = "broken"


class AllureReportSummary(Base):
    """
    Allure Report Summary - 每次测试执行的汇总记录
    对应一次完整的测试运行（一个 build）
    """
    __tablename__ = "allure_report_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ============ 关联信息 ============
    # 关联到 release_candidate_tests（可选，用于关联现有测试记录）
    release_test_id = Column(UUID(as_uuid=True), ForeignKey('release_candidate_tests.id', ondelete='SET NULL'),
                             nullable=True, index=True)

    # ============ 版本和平台信息 ============
    build_number = Column(String, nullable=False, index=True)  # e.g., "0022"
    version = Column(String, nullable=False, index=True)  # e.g., "6.4.0"
    project = Column(String, nullable=False, default="ftm", index=True)  # ftm, fortiexplorer, fortiedr
    platform = Column(String, nullable=False, index=True)  # android_15, ios_16, etc.

    # ============ Jenkins 信息 ============
    jenkins_job_name = Column(String, nullable=True, index=True)
    jenkins_build_number = Column(Integer, nullable=True)
    jenkins_build_url = Column(String, nullable=True)

    # ============ 汇总统计 ============
    total = Column(Integer, default=0)
    passed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    broken_count = Column(Integer, default=0)

    # 持续时间（毫秒）
    duration_ms = Column(BigInteger, default=0)

    # Pass rate (冗余字段，便于查询)
    pass_rate = Column(Float, default=0.0)  # 0.0 - 100.0

    # ============ 时间信息 ============
    report_timestamp = Column(DateTime, nullable=True)  # Allure 报告中的时间
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ============ 元数据 ============
    # 存储额外的元数据，如测试环境、设备信息等
    meta_data = Column("meta_data", JSON, default=dict)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "release_test_id": str(self.release_test_id) if self.release_test_id else None,
            "build_number": self.build_number,
            "version": self.version,
            "project": self.project,
            "platform": self.platform,
            "jenkins_job_name": self.jenkins_job_name,
            "jenkins_build_number": self.jenkins_build_number,
            "jenkins_build_url": self.jenkins_build_url,
            "total": self.total,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "broken_count": self.broken_count,
            "duration_ms": self.duration_ms,
            "pass_rate": self.pass_rate,
            "report_timestamp": self.report_timestamp.isoformat() if self.report_timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "meta_data": self.meta_data,
        }


class AllureTestCase(Base):
    """
    Allure Test Case - 单个测试用例的执行结果
    每条记录对应一个测试用例的一次执行
    """
    __tablename__ = "allure_test_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ============ 关联到 Summary ============
    summary_id = Column(UUID(as_uuid=True), ForeignKey('allure_report_summaries.id', ondelete='CASCADE'),
                        nullable=False, index=True)

    # ============ 测试用例信息 ============
    name = Column(String, nullable=False, index=True)  # 测试用例名称
    test_class = Column(String, nullable=True)  # 测试类名
    test_method = Column(String, nullable=True)  # 测试方法名

    # ============ Suite 层级结构 ============
    parent_suite = Column(String, nullable=True, index=True)  # 父 Suite
    suite = Column(String, nullable=True, index=True)  # Suite
    sub_suite = Column(String, nullable=True)  # 子 Suite

    # ============ 测试结果 ============
    status = Column(SQLEnum(TestStatusEnum), nullable=False, index=True)
    duration_ms = Column(BigInteger, default=0)  # 持续时间（毫秒）

    # ============ 错误信息 ============
    error_message = Column(Text, nullable=True)  # 错误摘要
    error_trace = Column(Text, nullable=True)  # 完整错误堆栈（可选存储）

    # ============ 时间信息 ============
    start_time = Column(DateTime, nullable=True)
    stop_time = Column(DateTime, nullable=True)

    # ============ 元数据 ============
    # 存储标签、参数化信息等
    meta_data = Column("meta_data", JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "summary_id": str(self.summary_id),
            "name": self.name,
            "test_class": self.test_class,
            "test_method": self.test_method,
            "parent_suite": self.parent_suite,
            "suite": self.suite,
            "sub_suite": self.sub_suite,
            "status": self.status.value if self.status else None,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "stop_time": self.stop_time.isoformat() if self.stop_time else None,
            "meta_data": self.meta_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AllureTestTrend(Base):
    """
    Allure Test Trend - 测试趋势统计表
    按天/版本聚合的统计数据，用于快速生成趋势图
    这是一个物化视图（Materialized View）的持久化表
    """
    __tablename__ = "allure_test_trends"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ============ 聚合维度 ============
    project = Column(String, nullable=False, index=True)
    platform = Column(String, nullable=False, index=True)
    version = Column(String, nullable=False, index=True)
    build_number = Column(String, nullable=False, index=True)

    # 日期分区（用于趋势查询）
    report_date = Column(DateTime, nullable=False, index=True)  # 按天分区

    # ============ 汇总统计 ============
    total = Column(Integer, default=0)
    passed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    broken_count = Column(Integer, default=0)
    duration_ms = Column(BigInteger, default=0)
    pass_rate = Column(Float, default=0.0)

    # ============ 失败分析 ============
    # Top N 失败用例（JSON 存储）
    top_failures = Column(JSON, default=list)  # [{"name": "...", "count": 1}]

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "project": self.project,
            "platform": self.platform,
            "version": self.version,
            "build_number": self.build_number,
            "report_date": self.report_date.isoformat() if self.report_date else None,
            "total": self.total,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "broken_count": self.broken_count,
            "duration_ms": self.duration_ms,
            "pass_rate": self.pass_rate,
            "top_failures": self.top_failures,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
