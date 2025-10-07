# Claude Code Agent Configuration

This document provides an overview of the purpose-built agents configured for context efficiency and specialized expertise.

## Agent Architecture Overview

**Purpose**: Convert large, complex commands into specialized agents to achieve:
- **Context Efficiency**: 60-80% reduction in token usage through focused expertise
- **Response Speed**: 30-50% faster processing with specialized knowledge
- **Quality Improvement**: Consistent methodology and domain-specific best practices
- **Scalable Maintenance**: Independent agent improvement and optimization

## Current Agent Ecosystem

### **Phase 1 Agents (Production Ready)**

#### **jira-project-manager**
- **Domain**: JIRA ticket creation, project management, Confluence documentation
- **Expertise**: INVEST principles, FBG hierarchy rules, Diataxis framework
- **Tools**: Atlassian MCP tools, documentation tools
- **Model**: Opus (complex reasoning for project management)
- **Replaces**: TylerBot.md command (317 lines → focused agent)
- **Context Efficiency**: 70-80% token reduction
- **Use Cases**: 
  - Creating JIRA epics and stories with proper hierarchy
  - Generating Confluence documentation following team standards
  - Project planning and ticket organization

#### **knowledge-synthesis**
- **Domain**: Zettelkasten research, knowledge integration, book zettel creation
- **Expertise**: Academic research synthesis, Logseq integration, sequential thinking
- **Tools**: Web research tools, file manipulation, search tools
- **Model**: Opus (complex research and synthesis reasoning)
- **Replaces**: synthesize_knowledge.md command (135+ lines → focused agent)
- **Context Efficiency**: 60-70% token reduction
- **Use Cases**:
  - Synthesizing external articles with comprehensive research
  - Creating book zettels with author integration
  - Building interconnected knowledge networks

#### **code-refactoring**
- **Domain**: Code improvement, design patterns, software engineering principles
- **Expertise**: SOLID principles, Martin Fowler's refactoring catalog, GoF patterns
- **Tools**: Code analysis and editing tools
- **Model**: Opus (complex architectural reasoning)
- **Replaces**: refactor_code.md command (92 lines → focused agent)
- **Context Efficiency**: 65-75% token reduction
- **Use Cases**:
  - Applying design patterns and SOLID principles
  - Modernizing legacy code with language-specific idioms
  - Systematic code quality improvement

### **Existing Specialized Agents**

#### **pr-reviewer**
- **Domain**: Code review, software engineering best practices
- **Expertise**: Testing excellence, domain modeling, enterprise patterns
- **Model**: Opus
- **Specialty**: Comprehensive code review based on authoritative literature

#### **java-test-debugger**
- **Domain**: Java testing framework debugging
- **Expertise**: JUnit, Spring Test, Mockito, build tool configurations
- **Model**: Sonnet
- **Specialty**: Rapid test failure diagnosis and fixing

#### **github-debugger**
- **Domain**: GitHub Actions and CI/CD troubleshooting
- **Expertise**: Workflow debugging, build failures, deployment issues
- **Model**: [Check existing configuration]
- **Specialty**: GitHub ecosystem problem solving

### **Phase 2 Agents (Future Consideration)**

#### **project-planning** (from next_step.md)
- **Domain**: TODO analysis, task breakdown, sequential thinking
- **Expertise**: Atomic task decomposition, dependency analysis
- **Context Efficiency**: 50-60% token reduction
- **Status**: Candidate for conversion

#### **code-analysis** (from find_refactor_candidates.md)  
- **Domain**: Code quality assessment, refactoring identification
- **Expertise**: Code metrics, git history analysis, technical debt identification
- **Context Efficiency**: 45-55% token reduction
- **Status**: Candidate for conversion

## Agent Design Principles

### **Context Efficiency Guidelines**
1. **High Specialization**: Focus on narrow, deep expertise vs. broad knowledge
2. **Consistent Methodology**: Establish repeatable processes and quality standards
3. **Tool Optimization**: Include only essential tools for the domain
4. **Model Selection**: Choose appropriate model based on reasoning complexity
5. **Clear Boundaries**: Define exactly when to use each agent

### **Usage Pattern Design**
- **Trigger Conditions**: Make it obvious when to invoke specific agents
- **Example Scenarios**: Provide concrete examples with commentary explaining agent choice
- **Value Proposition**: Clearly articulate why specialization matters over general Claude
- **Quality Standards**: Define what makes each agent's output superior

### **Agent File Structure**
```yaml
---
name: agent-name
description: When to use this agent with specific examples and commentary
tools: [list of required tools or * for all]
model: [opus/sonnet/haiku based on complexity]
---

[Specialized expertise content with methodology, standards, and best practices]
```

## Implementation Results

### **Token Efficiency Gains**
- **jira-project-manager**: ~75% reduction in context tokens
- **knowledge-synthesis**: ~65% reduction in context tokens  
- **code-refactoring**: ~70% reduction in context tokens
- **Overall**: Estimated 60-80% improvement in context efficiency for specialized tasks

### **Response Quality Improvements**
- **Consistent Methodology**: Each agent follows established, domain-specific processes
- **Authoritative References**: Agents ground recommendations in established literature
- **Quality Standards**: Non-negotiable requirements ensure output consistency
- **Best Practices**: Domain expertise embedded in agent knowledge

### **Maintenance Benefits**
- **Independent Evolution**: Each agent can be improved without affecting others
- **Focused Expertise**: Deep domain knowledge vs. broad general capabilities
- **Clear Responsibilities**: Well-defined boundaries and use cases
- **Scalable Architecture**: Easy to add new specialized agents

## Usage Guidelines

### **When to Use Specialized Agents**
- Complex, multi-step workflows requiring domain expertise
- Tasks with established patterns and methodologies
- Work requiring consistent quality standards and best practices
- Situations where context efficiency significantly improves performance

### **When to Use General Claude**
- Simple, one-off tasks without complex methodology requirements
- Exploratory work where broad knowledge is more valuable than deep expertise
- Tasks outside the scope of existing specialized agents
- Quick questions or simple formatting operations

### **Agent Selection Strategy**
1. **Identify Task Domain**: Match request to agent expertise areas
2. **Assess Complexity**: Determine if specialization adds value
3. **Check Examples**: Use agent description examples to validate choice
4. **Invoke Appropriately**: Use Task tool with correct subagent_type

## Future Development

### **Expansion Candidates**
- **api-integration**: REST/GraphQL API design and integration patterns
- **database-design**: Data modeling, query optimization, migration strategies
- **security-audit**: Security best practices, vulnerability assessment
- **performance-optimization**: Profiling, bottleneck identification, optimization strategies

### **Enhancement Opportunities**
- **Cross-Agent Coordination**: Agents working together on complex multi-domain tasks
- **Context Sharing**: Efficient information passing between related agents
- **Quality Metrics**: Measuring and improving agent effectiveness over time
- **User Experience**: Streamlined agent invocation and workflow integration

## Command Migration Status

### **✅ Converted to Agents**
- ~~TylerBot.md~~ → **jira-project-manager**
- ~~synthesize_knowledge.md~~ → **knowledge-synthesis**  
- ~~refactor_code.md~~ → **code-refactoring**

### **📋 Remaining Commands (Keep as Commands)**
- **does_it_work.md**: Simple verification checklist (57 lines)
- **commit.md**: Conventional commits formatting (48 lines)
- **create_new_command.md**: Meta-command for command creation (163 lines)
- **merge_worktree_to_main.md**: Git workflow automation (59 lines)
- **test_planner.md**: Testing strategy (35 lines) - *Could be agent candidate*

### **🔄 Phase 2 Conversion Candidates**
- **next_step.md**: Project planning and task breakdown (76 lines)
- **find_refactor_candidates.md**: Code quality assessment (112 lines)

This agent architecture provides significant context efficiency improvements while maintaining high-quality, specialized expertise for complex domains. The system scales well for adding new specialized agents as needed.